from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.urls import reverse
from django.utils.timezone import now, make_aware
from django.contrib.auth.models import User
from .models import Po, Fornecedor, StockEntradas, StockSaidas, UpdateStock, fioSaidas , updateFios, updatePo, CategoriaProduto
from .models import  Fios, poSaidas, poEntradas, FioTransformacao, FioTransformacaoItem, Stock , Agulhas, AgulhasEntradas, AgulhasSaidas, UpdateAgulhas
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import F, Sum, Value, CharField, IntegerField
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.utils import timezone


def index(request):
    users = User.objects.all()
    return render(request, 'management/index.html', {'users': users})

def menu_stock(request):
    return render(request, 'management/menu_stock.html')

def menu_fio(request):
    return render(request, 'management/menu_fio.html')

def menu_po(request):  
    return render(request, 'management/menu_po.html')

def menu_agulhas(request):
    return render(request, 'management/menu_agulhas.html')

def main_menu(request):
    return render(request, 'management/menu_main.html')

def user_logout(request):
    logout(request)
    messages.success(request, "Saiu da sua conta com sucesso!")
    return redirect('login', 0)

def login_view(request, user_id=None):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        password = request.POST.get('password', '')

        auth_user = authenticate(request, username=user.username, password=password)
        if auth_user is not None:
            auth_login(request, auth_user)  # cria a sessão
            messages.success(request, f'Bem-vindo, {auth_user.username}!')
            # PRG: redireciona para evitar repost em refresh
            return redirect('index')  # ou outra página, por ex. 'listar_pos'
        else:
            messages.error(request, 'Palavra-passe inválida.')

    return render(request, 'management/login.html', {'user': user})

def novo_fio(request):
    fornecedores = Fornecedor.objects.order_by('nome')
    material_choices = Fios._meta.get_field('material').choices  # [('cobre','Cobre'), ('aco','Aço')]

    if request.method == 'POST':
        size = request.POST.get('size')
        weight = request.POST.get('weight', '0')      # se quiser começar a 0, deixa '0'
        quantity = request.POST.get('quantity', '0')
        material = request.POST.get('material')
        min_stock = request.POST.get('min_stock', '0')
        fornecedor_id = request.POST.get('fornecedor')

        # validações simples
        try:
            fornecedor = Fornecedor.objects.get(id=fornecedor_id)
        except Fornecedor.DoesNotExist:
            messages.error(request, "Fornecedor inválido.")
            return render(request, 'management/novo_fio.html', {
                'fornecedores': fornecedores,
                'material_choices': material_choices,
                'form': request.POST,
            })

        try:
            size_dec = Decimal(size)
            weight_dec = Decimal(weight)
            quantity_int = int(quantity)
            min_stock_int = int(min_stock)
            if size_dec <= 0:
                raise InvalidOperation("Tamanho deve ser > 0.")
            if weight_dec < 0:
                raise InvalidOperation("Peso não pode ser negativo.")
            if quantity_int < 0 or min_stock_int < 0:
                raise InvalidOperation("Quantidade/Estoque mínimo não podem ser negativos.")
        except (InvalidOperation, ValueError):
            messages.error(request, "Verifique os valores numéricos informados.")
            return render(request, 'management/novo_fio.html', {
                'fornecedores': fornecedores,
                'material_choices': material_choices,
                'form': request.POST,
            })

        # cria o fio
        Fios.objects.create(
            size=size_dec,
            weight=weight_dec,
            quantity=quantity_int,
            material=material,
            min_stock=min_stock_int,
            fornecedor=fornecedor,
            user=request.user
        )
        messages.success(request, "Fio criado com sucesso!")
        # redireciona para evitar repost do formulário (ajusta a rota se quiser)
        return redirect('novo_fio')

    # GET
    return render(request, 'management/novo_fio.html', {
        'fornecedores': fornecedores,
        'material_choices': material_choices,
    })

def listar_pos(request):
    pos = Po.objects.all()
    fornecedor = Fornecedor.objects.all()
    today = now().date()
    filtro_data = request.GET.get('filtro_data')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Atualização via POST (incrementar/decrementar quantidade)
    if request.method == 'POST':
        po_id = request.POST.get('po_id')
        po_item = get_object_or_404(Po, id=po_id)

        if 'increment' in request.POST:
            po_item.quantity += 1
            action = 'added'
            prev_quantity = po_item.quantity - 1

        elif 'decrement' in request.POST:
            po_item.quantity -= 1
            action = 'removed'
            prev_quantity = po_item.quantity + 1
            print("Decrementing PO:", po_item.id)

        else:
            action = None

        if action:
            po_item.user = request.user
            po_item.save()
            updatePo.objects.create(
                po=po_item,
                previous_quantity=prev_quantity,
                new_quantity=po_item.quantity,
                user=request.user,
                action=action
            )

        if action == 'removed':
            poSaidas.objects.create(
                po=po_item,
                quantity_used=1,
                user=request.user
            )

        if action == 'added':
            poEntradas.objects.create(
                po=po_item,
                quantity_added=1,
                user=request.user
            )

        return redirect('listar_pos')

    return render(request, 'management/listar_pos.html', {
        'pos': pos,
        'fornecedor': fornecedor,
        'filtro_data': filtro_data,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })

def adicionarMaisde1Po(request, po_id):
    po = get_object_or_404(Po, pk=po_id)

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            po.quantity += quantidade
            po.user = request.user
            po.save()

            updatePo.objects.create(
                po=po,
                previous_quantity=po.quantity - quantidade,
                new_quantity=po.quantity,
                user=request.user,
                action='added'
            )

            poEntradas.objects.create(
                po=po,
                quantity_added=quantidade,
                user=request.user
            )

            return redirect('listar_pos')

        except ValueError:
            context = {'po': po, 'error': "Por favor, insira um número válido maior que zero."}
            return render(request, 'management/adicionar_po.html', context)

    return render(request, 'management/adicionar_po.html', {'po': po})


def removerPo(request, po_id):
    po = get_object_or_404(Po, pk=po_id)
    context = {'po': po}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            po.quantity -= quantidade
            po.user = request.user
            po.save()

            update_po = updatePo(
                po=po,
                previous_quantity=po.quantity + quantidade,
                new_quantity=po.quantity,
                user=request.user,
                action='removed'
            )
            update_po.save()


            poSaidas.objects.create(
                po=po,
                quantity_used=quantidade,
                user=request.user
            )

            context['success'] = True

            return redirect('listar_pos')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."

    return render(request, 'management/remover_po.html', context)

def listar_updates(request):
    updates = updatePo.objects.all()
    return render(request, 'management/listar_update_pos.html', {'updates': updates})


def listar_fios(request):
    if request.method == 'POST':
        fio_id = request.POST.get('fio_id')
        if fio_id:
            fio_item = Fios.objects.get(id=fio_id)
            if 'increment' in request.POST:
                fio_item.quantity += 1

                update_fios = updateFios(
                    fio=fio_item,
                    previous_quantity=fio_item.quantity - 1,
                    new_quantity=fio_item.quantity,
                    user=request.user,
                    action='increment'
                )
                update_fios.save()
            elif 'decrement' in request.POST:
                fio_item.quantity -= 1
                update_fios = updateFios(
                    fio=fio_item,
                    previous_quantity=fio_item.quantity + 1,
                    new_quantity=fio_item.quantity,
                    user=request.user,
                    action='decrement'
                )
                update_fios.save()
            fio_item.save()
            fio_item.user = request.user
            fio_item.save()

        return redirect('listar_fios')

    fios = Fios.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/listar_fios.html', {'fios': fios, 'fornecedor': fornecedor})

def adicionarMaisde1Fio(request, fio_id):
    fio = get_object_or_404(Fios, pk=fio_id)
    context = {'fio': fio}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            fio.quantity += quantidade
            fio.user = request.user
            fio.save()

            update_fio = updateFios(
                fio=fio,
                previous_quantity=fio.quantity - quantidade,
                new_quantity=fio.quantity,
                user=request.user,
                action='added'
            )
            update_fio.save()

            context['success'] = True

            return redirect('listar_fios')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."
            return render(request, 'management/adicionar_fio.html', context)

    return render(request, 'management/adicionar_fio.html', context)

def removerFio(request, fio_id):
    fio = get_object_or_404(Fios, pk=fio_id)
    context = {'fio': fio}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            fio.quantity -= quantidade
            fio.user = request.user
            fio.save()

            update_fio = updateFios(
                fio=fio,
                previous_quantity=fio.quantity + quantidade,
                new_quantity=fio.quantity,
                user=request.user,
                action='removed'
            )
            update_fio.save()

            context['success'] = True

            return redirect('listar_fios')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."

    return render(request, 'management/remover_fio.html', context)

def listar_updates_fios(request):
    updates = updateFios.objects.all()
    return render(request, 'management/listar_update_fios.html', {'updates': updates})


def historico_fios(request):
    filtro_data = request.GET.get("filtro_data", "hoje")
    data_inicio = request.GET.get("data_inicio")
    data_fim    = request.GET.get("data_fim")
    user_id     = request.GET.get("user_id", "0")
    tipo        = request.GET.get("tipo", "todos")  # "todos" | "entradas" | "saidas"
    incluir_legacy = request.GET.get("incluir_legacy") == "1"  # inclui fioSaidas se True

    di, df = _range_por_filtro(filtro_data, data_inicio, data_fim)

    upd = (updateFios.objects
           .select_related("fio", "user")
           .filter(date_updated__range=(di, df)))

    if user_id and user_id.isdigit() and int(user_id) != 0:
        upd = upd.filter(user__id=int(user_id))

    # quantidade alterada (sempre positiva), separando por action
    upd_add = (upd.filter(action="added")
        .annotate(
            date=F("date_updated"),
            quantity=F("new_quantity") - F("previous_quantity"),
            direction=Value("entrada", output_field=CharField()),
            fio_size=F("fio__size"),
            fio_weight=F("fio__weight"),
            fio_material=F("fio__material"),
            current_stock=F("fio__quantity"),
            username=F("user__username"),
        )
        .values("date","quantity","direction","fio_size","fio_weight","fio_material","current_stock","username")
    )

    upd_rem = (upd.filter(action="removed")
        .annotate(
            date=F("date_updated"),
            quantity=F("previous_quantity") - F("new_quantity"),
            direction=Value("saida", output_field=CharField()),
            fio_size=F("fio__size"),
            fio_weight=F("fio__weight"),
            fio_material=F("fio__material"),
            current_stock=F("fio__quantity"),
            username=F("user__username"),
        )
        .values("date","quantity","direction","fio_size","fio_weight","fio_material","current_stock","username")
    )

    # opcional: também juntar as saídas antigas (fioSaidas)
    legacy = fioSaidas.objects.none()
    if incluir_legacy:
        legacy = (fioSaidas.objects
            .select_related("fio","user")
            .filter(date_used__range=(di, df)))
        if user_id and user_id.isdigit() and int(user_id) != 0:
            legacy = legacy.filter(user__id=int(user_id))
        legacy_norm = (legacy
            .annotate(
                date=F("date_used"),
                quantity=F("quantity_used"),
                direction=Value("saida", output_field=CharField()),
                fio_size=F("fio__size"),
                fio_weight=F("fio__weight"),
                fio_material=F("fio__material"),
                current_stock=F("fio__quantity"),
                username=F("user__username"),
            )
            .values("date","quantity","direction","fio_size","fio_weight","fio_material","current_stock","username")
        )
    else:
        legacy_norm = None

    # aplicar filtro tipo
    if tipo == "entradas":
        historico = upd_add
    elif tipo == "saidas":
        historico = upd_rem if not legacy_norm else upd_rem.union(legacy_norm, all=True)
    else:
        historico = upd_add.union(upd_rem, all=True)
        if legacy_norm:
            historico = historico.union(legacy_norm, all=True)

    historico = historico.order_by("-date")

    # totais (só com UpdateFios; se incluir_legacy, somamos também)
    total_entradas = (upd_add.aggregate(total=Sum("quantity"))["total"] or 0)
    total_saidas   = (upd_rem.aggregate(total=Sum("quantity"))["total"] or 0)
    if incluir_legacy:
        total_saidas_legacy = legacy.aggregate(total=Sum("quantity_removed"))["total"] or 0
        total_saidas += total_saidas_legacy

    if tipo == "entradas":
        total_listado = total_entradas
    elif tipo == "saidas":
        total_listado = total_saidas
    else:
        total_listado = None

    # resumo por (size, weight, material)
    ent_por_fio = (upd_add
        .values("fio_size","fio_weight","fio_material")
        .annotate(total_ent=Sum("quantity"))
    )
    sai_por_fio = (upd_rem
        .values("fio_size","fio_weight","fio_material")
        .annotate(total_sai=Sum("quantity"))
    )
    if incluir_legacy:
        sai_legacy = (legacy
            .values("fio__size","fio__weight","fio__material")
            .annotate(total_sai=Sum("quantity_removed"))
        )
    else:
        sai_legacy = []

    # merge dos mapas
    resumo_map = {}
    for row in ent_por_fio:
        k = (row["fio_size"], row["fio_weight"], row["fio_material"])
        resumo_map[k] = {
            "size": k[0], "weight": k[1], "material": k[2],
            "entradas": row["total_ent"] or 0, "saidas": 0
        }
    for row in sai_por_fio:
        k = (row["fio_size"], row["fio_weight"], row["fio_material"])
        if k not in resumo_map:
            resumo_map[k] = {"size": k[0], "weight": k[1], "material": k[2], "entradas": 0, "saidas": row["total_sai"] or 0}
        else:
            resumo_map[k]["saidas"] += row["total_sai"] or 0
    for row in sai_legacy:
        k = (row["fio__size"], row["fio__weight"], row["fio__material"])
        if k not in resumo_map:
            resumo_map[k] = {"size": k[0], "weight": k[1], "material": k[2], "entradas": 0, "saidas": row["total_sai"] or 0}
        else:
            resumo_map[k]["saidas"] += row["total_sai"] or 0

    resumo_por_fio = []
    for v in resumo_map.values():
        v["saldo"] = (v["entradas"] or 0) - (v["saidas"] or 0)
        resumo_por_fio.append(v)
    resumo_por_fio.sort(key=lambda x: (x["material"], x["size"], x["weight"]))

    users = User.objects.all().order_by("username")

    ctx = {
        "registos": historico,
        "filtro_data": filtro_data,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "user_id": int(user_id) if user_id.isdigit() else 0,
        "users": users,
        "tipo": tipo,

        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_total": total_entradas - total_saidas,
        "total_listado": total_listado,

        "resumo_por_fio": resumo_por_fio,
        "incluir_legacy": incluir_legacy,
    }
    return render(request, "management/historico_fios.html", ctx)


def filtrar_po_saidas(request):
    today = now().date()
    filtro_data = request.GET.get('filtro_data', 'hoje')
    data_inicio = request.GET.get('data_inicio')  # 'YYYY-MM-DD'
    data_fim = request.GET.get('data_fim')        # 'YYYY-MM-DD'
    user_id = request.GET.get('user_id')          # id do utilizador (string)

    qs = poSaidas.objects.select_related('po', 'user')

    # --- filtro por datas ---
    if filtro_data == 'hoje':
        qs = qs.filter(date_used__date=today)
    elif filtro_data == 'ontem':
        ontem = today - timedelta(days=1)
        qs = qs.filter(date_used__date=ontem)
    elif filtro_data == 'semana':
        inicio_semana = today - timedelta(days=today.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        qs = qs.filter(date_used__date__range=(inicio_semana, fim_semana))
    elif filtro_data == 'mes':
        qs = qs.filter(date_used__year=today.year, date_used__month=today.month)
    elif filtro_data == 'ano':
        qs = qs.filter(date_used__year=today.year)
    elif filtro_data == 'entre' and data_inicio and data_fim:
        try:
            dt_inicio = make_aware(datetime.strptime(data_inicio, "%Y-%m-%d"))
            dt_fim = make_aware(datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)) - timedelta(seconds=1)
            qs = qs.filter(date_used__range=(dt_inicio, dt_fim))
        except ValueError:
            pass

    # --- filtro por utilizador (opcional) ---
    # aceita também '0' ou vazio como "todos"
    if user_id and user_id not in ('0', ''):
        qs = qs.filter(user__id=user_id)

    # Totais e resumo baseados no queryset filtrado
    total_usado = qs.aggregate(total=Sum('quantity_used'))['total'] or 0
    resumo_por_po = (
        qs.values('po__id', 'po__product', 'po__reference')
          .annotate(total=Sum('quantity_used'))
          .order_by('po__product', 'po__reference')
    )

    # Lista de utilizadores para o select
    users = User.objects.order_by('username').values('id', 'username')

    context = {
        'registos': qs.order_by('-date_used'),
        'total_usado': total_usado,
        'resumo_por_po': resumo_por_po,
        'filtro_data': filtro_data,
        'data_inicio': data_inicio or '',
        'data_fim': data_fim or '',
        'user_id': int(user_id) if user_id and user_id.isdigit() else 0,
        'users': users,
    }
    return render(request, 'management/po_saidas_filtro.html', context)


def filtrar_po_entradas(request):
    today = now().date()
    filtro_data = request.GET.get('filtro_data', 'hoje')
    data_inicio = request.GET.get('data_inicio')  # 'YYYY-MM-DD'
    data_fim = request.GET.get('data_fim')        # 'YYYY-MM-DD'
    user_id = request.GET.get('user_id')          # id do utilizador (string)

    qs = poEntradas.objects.select_related('po', 'user')

    # --- filtro por datas ---
    if filtro_data == 'hoje':
        qs = qs.filter(date_added__date=today)
    elif filtro_data == 'ontem':
        ontem = today - timedelta(days=1)
        qs = qs.filter(date_added__date=ontem)
    elif filtro_data == 'semana':
        inicio_semana = today - timedelta(days=today.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        qs = qs.filter(date_added__date__range=(inicio_semana, fim_semana))
    elif filtro_data == 'mes':
        qs = qs.filter(date_added__year=today.year, date_added__month=today.month)
    elif filtro_data == 'ano':
        qs = qs.filter(date_added__year=today.year)
    elif filtro_data == 'entre' and data_inicio and data_fim:
        try:
            dt_inicio = make_aware(datetime.strptime(data_inicio, "%Y-%m-%d"))
            dt_fim = make_aware(datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)) - timedelta(seconds=1)
            qs = qs.filter(date_added__range=(dt_inicio, dt_fim))
        except ValueError:
            pass

    # --- filtro por utilizador (opcional) ---
    # aceita também '0' ou vazio como "todos"
    if user_id and user_id not in ('0', ''):
        qs = qs.filter(user__id=user_id)

    # Totais e resumo baseados no queryset filtrado
    total_usado = qs.aggregate(total=Sum('quantity_added'))['total'] or 0
    resumo_por_po = (
        qs.values('po__id', 'po__product', 'po__reference')
          .annotate(total=Sum('quantity_added'))
          .order_by('po__product', 'po__reference')
    )

    # Lista de utilizadores para o select
    users = User.objects.order_by('username').values('id', 'username')

    context = {
        'registos': qs.order_by('-date_added'),
        'total_usado': total_usado,
        'resumo_por_po': resumo_por_po,
        'filtro_data': filtro_data,
        'data_inicio': data_inicio or '',
        'data_fim': data_fim or '',
        'user_id': int(user_id) if user_id and user_id.isdigit() else 0,
        'users': users,
    }
    return render(request, 'management/po_entradas_filtro.html', context)

# management/views.py
from datetime import date, datetime, timedelta
from django.utils import timezone

def _make_day_bounds(d: date):
    """
    Devolve (inicio_do_dia, fim_do_dia) como datetimes aware no timezone atual.
    """
    tz = timezone.get_current_timezone()
    start_naive = datetime.combine(d, datetime.min.time())
    end_naive   = datetime.combine(d, datetime.max.time())
    start = timezone.make_aware(start_naive, tz) if timezone.is_naive(start_naive) else start_naive
    end   = timezone.make_aware(end_naive, tz)   if timezone.is_naive(end_naive)   else end_naive
    return start, end


def _range_por_filtro(filtro_data, data_inicio_str, data_fim_str):
    """
    Converte o filtro de período em (inicio, fim) timezone-aware.
    """
    hoje = timezone.localdate()  # devolve date no tz atual

    if filtro_data == "entre" and data_inicio_str and data_fim_str:
        di_date = date.fromisoformat(data_inicio_str)
        df_date = date.fromisoformat(data_fim_str)
        di, _ = _make_day_bounds(di_date)
        _, df = _make_day_bounds(df_date)
        return di, df

    if filtro_data == "ontem":
        d = hoje - timedelta(days=1)
        return _make_day_bounds(d)

    if filtro_data == "semana":
        # segunda -> domingo
        inicio_sem = hoje - timedelta(days=hoje.weekday())
        fim_sem = inicio_sem + timedelta(days=6)
        di, _ = _make_day_bounds(inicio_sem)
        _, df = _make_day_bounds(fim_sem)
        return di, df

    if filtro_data == "mes":
        inicio_mes = hoje.replace(day=1)
        # próximo mês dia 1
        if inicio_mes.month == 12:
            prox = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1)
        else:
            prox = inicio_mes.replace(month=inicio_mes.month + 1, day=1)
        fim_mes = prox - timedelta(days=1)
        di, _ = _make_day_bounds(inicio_mes)
        _, df = _make_day_bounds(fim_mes)
        return di, df

    if filtro_data == "ano":
        inicio_ano = hoje.replace(month=1, day=1)
        fim_ano    = hoje.replace(month=12, day=31)
        di, _ = _make_day_bounds(inicio_ano)
        _, df = _make_day_bounds(fim_ano)
        return di, df

    # default: hoje
    return _make_day_bounds(hoje)



def historico_po(request):
    filtro_data = request.GET.get("filtro_data", "hoje")
    data_inicio = request.GET.get("data_inicio")
    data_fim    = request.GET.get("data_fim")
    user_id     = request.GET.get("user_id", "0")
    tipo        = request.GET.get("tipo", "todos")  # "todos" | "entradas" | "saidas"

    di, df = _range_por_filtro(filtro_data, data_inicio, data_fim)

    # Base querysets com filtros de tempo
    ent = (poEntradas.objects
           .select_related("po", "user")
           .filter(date_added__range=(di, df)))
    sai = (poSaidas.objects
           .select_related("po", "user")
           .filter(date_used__range=(di, df)))

    # Filtro por utilizador (opcional)
    if user_id and user_id.isdigit() and int(user_id) != 0:
        ent = ent.filter(user__id=int(user_id))
        sai = sai.filter(user__id=int(user_id))

    # Normalizar campos para UNIÓN (têm os mesmos nomes/ordens)
    ent_norm = (ent
        .annotate(
            date=F("date_added"),
            quantity=F("quantity_added"),
            direction=Value("entrada", output_field=CharField()),
            po_product=F("po__product"),
            po_reference=F("po__reference"),
            current_stock=F("po__quantity"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "po_product", "po_reference", "current_stock", "username")
    )

    sai_norm = (sai
        .annotate(
            date=F("date_used"),
            quantity=F("quantity_used"),
            direction=Value("saida", output_field=CharField()),
            po_product=F("po__product"),
            po_reference=F("po__reference"),
            current_stock=F("po__quantity"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "po_product", "po_reference", "current_stock", "username")
    )

    # Aplicar filtro por tipo
    if tipo == "entradas":
        historico = ent_norm
    elif tipo == "saidas":
        historico = sai_norm
    else:
        historico = ent_norm.union(sai_norm, all=True)

    # Ordenação (só pode após union)
    historico = historico.order_by("-date")

    # Totais
    total_entradas = ent.aggregate(total=Sum("quantity_added"))["total"] or 0
    total_saidas   = sai.aggregate(total=Sum("quantity_used"))["total"] or 0

    if tipo == "entradas":
        total_listado = total_entradas
    elif tipo == "saidas":
        total_listado = total_saidas
    else:
        # Para "todos", mostramos dois totais e o saldo
        total_listado = None

    # Resumo por pó (Entradas, Saídas, Saldo)
    entradas_por_po = (ent
        .values("po__product", "po__reference")
        .annotate(total_ent=Sum("quantity_added"))
    )
    saidas_por_po = (sai
        .values("po__product", "po__reference")
        .annotate(total_sai=Sum("quantity_used"))
    )

    # Juntar os dois dicionários por (product, reference)
    resumo_map = {}
    for row in entradas_por_po:
        key = (row["po__product"], row["po__reference"])
        resumo_map[key] = {"product": key[0], "reference": key[1],
                           "entradas": row["total_ent"] or 0, "saidas": 0}
    for row in saidas_por_po:
        key = (row["po__product"], row["po__reference"])
        if key not in resumo_map:
            resumo_map[key] = {"product": key[0], "reference": key[1],
                               "entradas": 0, "saidas": row["total_sai"] or 0}
        else:
            resumo_map[key]["saidas"] = row["total_sai"] or 0

    resumo_por_po = []
    for v in resumo_map.values():
        v["saldo"] = (v["entradas"] or 0) - (v["saidas"] or 0)
        resumo_por_po.append(v)

    # Ordenar por produto/ref
    resumo_por_po.sort(key=lambda x: (x["product"], x["reference"]))

    users = User.objects.all().order_by("username")

    ctx = {
        "registos": historico,
        "filtro_data": filtro_data,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "user_id": int(user_id) if user_id and user_id.isdigit() else 0,
        "users": users,
        "tipo": tipo,

        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_total": total_entradas - total_saidas,
        "total_listado": total_listado,

        "resumo_por_po": resumo_por_po,
    }
    return render(request, "management/historico_po.html", ctx)

@login_required
def trafilar_fio(request):
    origem_id = request.GET.get('origem_id') or request.POST.get('origem_id')
    origem = get_object_or_404(Fios, id=origem_id) if origem_id else None

    destinos_qs = Fios.objects.none()
    fornecedores = Fornecedor.objects.order_by('nome')
    if origem:
        # destinos do mesmo material e tamanho diferente
        destinos_qs = Fios.objects.filter(material=origem.material).exclude(id=origem.id).order_by('size')

    if request.method == 'POST':
        if not origem:
            messages.error(request, "Selecione um fio de origem.")
            return redirect('trafilar_fio')

        target_ids = request.POST.getlist('target_id[]')  # ids de destino existentes
        weights    = request.POST.getlist('peso[]')       # pesos a transferir (g)

        pares = []
        for tid, w in zip(target_ids, weights):
            if (not tid or tid.strip() == '') and (not w or w.strip() == ''):
                continue
            pares.append((tid.strip(), w.strip()))

        if not pares:
            messages.error(request, "Adicione pelo menos um destino e peso.")
            return redirect(f"{request.path}?origem_id={origem.id}")

        # validação e consolidação
        vistos = {}  # destino.id -> soma peso
        total_transferir = Decimal('0')
        try:
            for tid, w in pares:
                if not tid:
                    raise ValueError("Selecione um destino existente ou crie um novo pelo botão 'Novo destino'.")
                destino = Fios.objects.get(id=tid)

                if destino.id == origem.id:
                    raise ValueError("O destino não pode ser o mesmo que a origem.")
                if destino.material != origem.material:
                    raise ValueError("Material do destino deve ser igual ao da origem.")

                peso = Decimal(w)
                if peso <= 0:
                    raise ValueError("Peso deve ser maior que zero.")

                key = f"{destino.id}"
                if key in vistos:
                    vistos[key] += peso
                else:
                    vistos[key] = peso

            total_transferir = sum(vistos.values(), Decimal('0'))

        except (Fios.DoesNotExist, InvalidOperation, ValueError) as e:
            messages.error(request, f"Erro de validação: {e}")
            return redirect(f"{request.path}?origem_id={origem.id}")

        if total_transferir > origem.weight:
            messages.error(request, f"Peso a transferir ({total_transferir}g) excede o disponível ({origem.weight}g).")
            return redirect(f"{request.path}?origem_id={origem.id}")

        # transação: debita origem, credita destinos e regista log
        with transaction.atomic():
            peso_origem_antes = origem.weight

            origem.weight = F('weight') - total_transferir
            origem.user = request.user
            update_fields = ['weight', 'user']
            if hasattr(origem, 'updated_at'):
                update_fields.append('updated_at')
            origem.save(update_fields=update_fields)
            origem.refresh_from_db(fields=['weight'])
            peso_origem_depois = origem.weight

            transf = FioTransformacao.objects.create(
                origem=origem,
                total_transferido=total_transferir,
                peso_origem_antes=peso_origem_antes,
                peso_origem_depois=peso_origem_depois,
                user=request.user
            )

            for dest_id, peso_add in vistos.items():
                destino = Fios.objects.get(id=dest_id)

                FioTransformacaoItem.objects.create(
                    transformacao=transf,
                    destino=destino,
                    peso_adicionado=peso_add
                )

                destino.weight = F('weight') + peso_add
                destino.user = request.user
                dest_update = ['weight', 'user']
                if hasattr(destino, 'updated_at'):
                    dest_update.append('updated_at')
                destino.save(update_fields=dest_update)

        messages.success(
            request,
            f"Transformação concluída. Transferido {total_transferir}g. Sobra na origem: {peso_origem_depois}g."
        )
        return redirect(f"{request.path}?origem_id={origem.id}")

    # GET
    fios = Fios.objects.order_by('material', 'size')
    context = {
        'fios': fios,
        'origem': origem,
        'destinos': destinos_qs,
        'fornecedores': fornecedores,
    }
    return render(request, 'management/trafilar_fio.html', context)


@login_required
def criar_fio_rapido(request):
    if request.method != 'POST':
        return redirect('trafilar_fio')

    origem_id = request.POST.get('origem_id')
    next_url  = request.POST.get('next') or (f"{reverse('trafilar_fio')}?origem_id={origem_id}" if origem_id else reverse('trafilar_fio'))

    origem = get_object_or_404(Fios, id=origem_id) if origem_id else None
    if not origem:
        messages.error(request, "Origem inválida.")
        return redirect(next_url)

    fornecedor_id = request.POST.get('fornecedor')
    size_str      = request.POST.get('size')
    min_stock     = request.POST.get('min_stock') or '0'
    quantity_init = request.POST.get('quantity') or '0'

    try:
        fornecedor = Fornecedor.objects.get(id=fornecedor_id)
        size = Decimal(size_str)
        if size <= 0:
            raise InvalidOperation("Tamanho inválido.")

        existente = Fios.objects.filter(
            material=origem.material,
            fornecedor=fornecedor,
            size=size
        ).first()

        if existente:
            messages.info(request, f"Fio {existente.size}mm já existia e pode ser usado como destino.")
        else:
            qty_init_int = int(quantity_init) if str(quantity_init).isdigit() else 0
            Fios.objects.create(
                size=size,
                weight=Decimal('0'),               # sempre 0
                quantity=qty_init_int,             # número de unidades, opcional
                material=origem.material,
                min_stock=int(min_stock),
                fornecedor=fornecedor,
                user=request.user
            )
            messages.success(request, "Novo fio criado com sucesso.")

    except Fornecedor.DoesNotExist:
        messages.error(request, "Fornecedor inválido.")
    except (InvalidOperation, ValueError):
        messages.error(request, "Dados inválidos ao criar fio.")

    return redirect(next_url)




def historico_trefilagens(request):
    today = now().date()

    filtro_data = request.GET.get('filtro_data', 'mes')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    user_id = request.GET.get('user_id', '')
    page = request.GET.get('page', 1)

    qs = (FioTransformacao.objects
          .select_related('origem', 'user')
          .prefetch_related(
              Prefetch('itens',
                       queryset=FioTransformacaoItem.objects.select_related('destino').order_by('destino__size'),
                       to_attr='itens_pref')
          )
          .order_by('-created_at'))

    # --- filtro por data ---
    if filtro_data == 'hoje':
        qs = qs.filter(created_at__date=today)
    elif filtro_data == 'ontem':
        d = today - timedelta(days=1)
        qs = qs.filter(created_at__date=d)
    elif filtro_data == 'semana':
        inicio = today - timedelta(days=today.weekday())
        fim = inicio + timedelta(days=6)
        qs = qs.filter(created_at__date__range=(inicio, fim))
    elif filtro_data == 'mes':
        qs = qs.filter(created_at__year=today.year, created_at__month=today.month)
    elif filtro_data == 'ano':
        qs = qs.filter(created_at__year=today.year)
    elif filtro_data == 'entre' and data_inicio and data_fim:
        try:
            di = make_aware(datetime.strptime(data_inicio, "%Y-%m-%d"))
            df = make_aware(datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)) - timedelta(seconds=1)
            qs = qs.filter(created_at__range=(di, df))
        except ValueError:
            pass  # datas inválidas: ignora (podes mostrar mensagem via messages)

    # --- filtro por utilizador ---
    if user_id and user_id not in ('0', '', None):
        qs = qs.filter(user__id=user_id)

    # paginação
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page)

    # lista de utilizadores para o select
    users = User.objects.order_by('username').values('id', 'username')

    context = {
        'page_obj': page_obj,
        'filtro_data': filtro_data,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'user_id': int(user_id) if str(user_id).isdigit() else 0,
        'users': users,
        'today': today.strftime("%Y-%m-%d"),
    }
    return render(request, 'management/historico_trefilagens.html', context)

def listar_stock(request):
    if request.method == 'POST':
        stock_id = request.POST.get('stock_id')
        if stock_id:
            stock_item = Stock.objects.get(id=stock_id)
            if 'increment' in request.POST:
                stock_item.quantity += 1

                update_stock = UpdateStock.objects.create(
                    stock=stock_item,
                    previous_quantity=stock_item.quantity - 1,
                    new_quantity=stock_item.quantity,
                    action='added',
                    user=request.user
                )

                StockEntradas.objects.create(
                    stock=stock_item,
                    quantity_added=1,
                    user=request.user
                )

            elif 'decrement' in request.POST:
                stock_item.quantity -= 1
                update_stock = UpdateStock.objects.create(
                    stock=stock_item,
                    previous_quantity=stock_item.quantity + 1,
                    new_quantity=stock_item.quantity,
                    action='removed',
                    user=request.user
                )

                StockSaidas.objects.create(
                    stock=stock_item,
                    quantity_removed=1,
                    user=request.user
                )

            stock_item.save()
            stock_item.user = request.user
            stock_item.save()



        return redirect('listar_stock')

    stock = Stock.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/listar_stock.html', {'stock': stock, 'fornecedor': fornecedor})


def adicionarStock(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            stock.quantity += quantidade
            stock.user = request.user
            stock.save()

            UpdateStock.objects.create(
                stock=stock,
                previous_quantity=stock.quantity - quantidade,
                new_quantity=stock.quantity,
                action='added',
                user=request.user
            )

            StockEntradas.objects.create(
                stock=stock,
                quantity_added=quantidade,
                user=request.user
            )

            return redirect('listar_stock')

        except ValueError:
            context = {'stock': stock, 'error': "Por favor, insira um número válido maior que zero."}
            return render(request, 'management/adicionar_stock.html', context)

    return render(request, 'management/adicionar_stock.html', {'stock': stock})


def removerStock(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)
    context = {'stock': stock}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            stock.quantity -= quantidade
            stock.user = request.user
            stock.save()

            UpdateStock.objects.create(
                stock=stock,
                previous_quantity=stock.quantity + quantidade,
                new_quantity=stock.quantity,
                action='removed',
                user=request.user
            )

            StockSaidas.objects.create(
                stock=stock,
                quantity_removed=quantidade,
                user=request.user
            )

            context['success'] = True

            return redirect('listar_stock')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."

    return render(request, 'management/remover_stock.html', context)

# management/views.py
from django.db.models import F, Sum, Value, CharField
from django.contrib.auth.models import User
from django.shortcuts import render
from .models import StockEntradas, StockSaidas, CategoriaProduto   # 👈 importa a categoria

def historico_stock(request):
    filtro_data = request.GET.get("filtro_data", "hoje")
    data_inicio = request.GET.get("data_inicio")
    data_fim    = request.GET.get("data_fim")
    user_id     = request.GET.get("user_id", "0")
    tipo        = request.GET.get("tipo", "todos")
    categoria_id = request.GET.get("categoria_id", "0")            # 👈 novo

    di, df = _range_por_filtro(filtro_data, data_inicio, data_fim)

    ent = (StockEntradas.objects
           .select_related("stock", "stock__categoria", "user")
           .filter(date_added__range=(di, df)))
    sai = (StockSaidas.objects
           .select_related("stock", "stock__categoria", "user")
           .filter(date_removed__range=(di, df)))

    # filtro por utilizador
    if user_id and user_id.isdigit() and int(user_id) != 0:
        ent = ent.filter(user__id=int(user_id))
        sai = sai.filter(user__id=int(user_id))

    # 🔎 filtro por categoria
    if categoria_id and categoria_id.isdigit() and int(categoria_id) != 0:
        ent = ent.filter(stock__categoria__id=int(categoria_id))
        sai = sai.filter(stock__categoria__id=int(categoria_id))

    # normalizar para unir (incluo categoria para poderes mostrar na tabela)
    ent_norm = (ent
        .annotate(
            date=F("date_added"),
            quantity=F("quantity_added"),
            direction=Value("entrada", output_field=CharField()),
            stock_product=F("stock__product"),
            current_stock=F("stock__quantity"),
            categoria_nome=F("stock__categoria__nome"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "stock_product", "current_stock", "categoria_nome", "username")
    )

    sai_norm = (sai
        .annotate(
            date=F("date_removed"),
            quantity=F("quantity_removed"),
            direction=Value("saida", output_field=CharField()),
            stock_product=F("stock__product"),
            categoria_nome=F("stock__categoria__nome"),
            current_stock=F("stock__quantity"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "stock_product", "current_stock", "categoria_nome", "username")
    )

    if tipo == "entradas":
        historico = ent_norm
    elif tipo == "saidas":
        historico = sai_norm
    else:
        historico = ent_norm.union(sai_norm, all=True)

    historico = historico.order_by("-date")

    total_entradas = ent.aggregate(total=Sum("quantity_added"))["total"] or 0
    total_saidas   = sai.aggregate(total=Sum("quantity_removed"))["total"] or 0

    total_listado = None
    if tipo == "entradas":
        total_listado = total_entradas
    elif tipo == "saidas":
        total_listado = total_saidas

    # resumo por produto (já respeita os filtros aplicados acima, incluindo categoria)
    entradas_por_prod = (ent.values("stock__product").annotate(total_ent=Sum("quantity_added")))
    saidas_por_prod   = (sai.values("stock__product").annotate(total_sai=Sum("quantity_removed")))

    resumo_map = {}
    for row in entradas_por_prod:
        k = row["stock__product"]
        resumo_map[k] = {"product": k, "entradas": row["total_ent"] or 0, "saidas": 0}
    for row in saidas_por_prod:
        k = row["stock__product"]
        if k not in resumo_map:
            resumo_map[k] = {"product": k, "entradas": 0, "saidas": row["total_sai"] or 0}
        else:
            resumo_map[k]["saidas"] = row["total_sai"] or 0

    resumo_por_stock = []
    for v in resumo_map.values():
        v["saldo"] = v["entradas"] - v["saidas"]
        resumo_por_stock.append(v)
    resumo_por_stock.sort(key=lambda x: x["product"])

    users = User.objects.all().order_by("username")
    categorias = CategoriaProduto.objects.all().order_by("nome")    # 👈 carregar lista

    ctx = {
        "registos": historico,
        "filtro_data": filtro_data,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "user_id": int(user_id) if user_id.isdigit() else 0,
        "users": users,
        "tipo": tipo,

        "categoria_id": int(categoria_id) if categoria_id.isdigit() else 0,  # 👈 para selected
        "categorias": categorias,                                             # 👈 para dropdown

        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_total": total_entradas - total_saidas,
        "total_listado": total_listado,

        "resumo_por_stock": resumo_por_stock,
    }
    return render(request, "management/historico_stock.html", ctx)


def listar_agulhas(request):
    if request.method == 'POST':
        agulha_id = request.POST.get('agulha_id')
        if agulha_id:
            agulha_item = Agulhas.objects.get(id=agulha_id)
            if 'increment' in request.POST:
                agulha_item.quantidade += 1

                update_agulha = UpdateAgulhas.objects.create(
                    agulha=agulha_item,
                    previous_quantity=agulha_item.quantidade - 1,
                    new_quantity=agulha_item.quantidade,
                    action='added',
                    user=request.user
                )

                AgulhasEntradas.objects.create(
                    agulha=agulha_item,
                    quantity_added=1,
                    user=request.user
                )

            elif 'decrement' in request.POST:
                agulha_item.quantidade -= 1
                update_agulha = UpdateAgulhas.objects.create(
                    agulha=agulha_item,
                    previous_quantity=agulha_item.quantidade + 1,
                    new_quantity=agulha_item.quantidade,
                    action='removed',
                    user=request.user
                )

                AgulhasSaidas.objects.create(
                    agulha=agulha_item,
                    quantity_removed=1,
                    user=request.user
                )

            agulha_item.save()
            agulha_item.user = request.user
            agulha_item.save()

        return redirect('listar_agulhas')

    agulhas = Agulhas.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/listar_agulhas.html', {'agulhas': agulhas, 'fornecedor': fornecedor})


def adicionar_agulha(request, agulha_id):
    agulha = get_object_or_404(Agulhas, pk=agulha_id)

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            agulha.quantidade += quantidade
            agulha.user = request.user
            agulha.save()

            UpdateAgulhas.objects.create(
                agulha=agulha,
                previous_quantity=agulha.quantidade - quantidade,
                new_quantity=agulha.quantidade,
                action='added',
                user=request.user
            )

            AgulhasEntradas.objects.create(
                agulha=agulha,
                quantity_added=quantidade,
                user=request.user
            )

            return redirect('listar_agulhas')

        except ValueError:
            context = {'agulha': agulha, 'error': "Por favor, insira um número válido maior que zero."}
            return render(request, 'management/adicionar_agulha.html', context)

    return render(request, 'management/adicionar_agulha.html', {'agulha': agulha})


def remover_agulha(request, agulha_id):
    agulha = get_object_or_404(Agulhas, pk=agulha_id)
    context = {'agulha': agulha}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            agulha.quantidade -= quantidade
            agulha.user = request.user
            agulha.save()

            UpdateAgulhas.objects.create(
                agulha=agulha,
                previous_quantity=agulha.quantidade + quantidade,
                new_quantity=agulha.quantidade,
                action='removed',
                user=request.user
            )

            AgulhasSaidas.objects.create(
                agulha=agulha,
                quantity_removed=quantidade,
                user=request.user
            )

            context['success'] = True

            return redirect('listar_agulhas')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."

    return render(request, 'management/remover_agulha.html', context)


def historico_agulhas(request):
    filtro_data = request.GET.get("filtro_data", "hoje")
    data_inicio = request.GET.get("data_inicio")
    data_fim    = request.GET.get("data_fim")
    user_id     = request.GET.get("user_id", "0")
    tipo        = request.GET.get("tipo", "todos")  # "todos" | "entradas" | "saidas"

    di, df = _range_por_filtro(filtro_data, data_inicio, data_fim)

    ent = (AgulhasEntradas.objects
           .select_related("agulha", "user")
           .filter(date_added__range=(di, df)))
    sai = (AgulhasSaidas.objects
           .select_related("agulha", "user")
           .filter(date_removed__range=(di, df)))

    if user_id and user_id.isdigit() and int(user_id) != 0:
        ent = ent.filter(user__id=int(user_id))
        sai = sai.filter(user__id=int(user_id))

    # Normalizar para unir
    ent_norm = (ent
        .annotate(
            date=F("date_added"),
            quantity=F("quantity_added"),
            direction=Value("entrada", output_field=CharField()),
            agulha_tipo=F("agulha__tipo"),
            agulha_tamanho=F("agulha__tamanho"),
            current_stock=F("agulha__quantidade"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "agulha_tipo", "agulha_tamanho", "current_stock", "username")
    )

    sai_norm = (sai
        .annotate(
            date=F("date_removed"),
            quantity=F("quantity_removed"),
            direction=Value("saida", output_field=CharField()),
            agulha_tipo=F("agulha__tipo"),
            agulha_tamanho=F("agulha__tamanho"),
            current_stock=F("agulha__quantidade"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "agulha_tipo", "agulha_tamanho", "current_stock", "username")
    )

    if tipo == "entradas":
        historico = ent_norm
    elif tipo == "saidas":
        historico = sai_norm
    else:
        historico = ent_norm.union(sai_norm, all=True)

    historico = historico.order_by("-date")

    # Totais
    total_entradas = ent.aggregate(total=Sum("quantity_added"))["total"] or 0
    total_saidas   = sai.aggregate(total=Sum("quantity_removed"))["total"] or 0

    if tipo == "entradas":
        total_listado = total_entradas
    elif tipo == "saidas":
        total_listado = total_saidas
    else:
        total_listado = None

    # Resumo por (tipo, tamanho)
    entradas_por_ag = (ent
        .values("agulha__tipo", "agulha__tamanho")
        .annotate(total_ent=Sum("quantity_added"))
    )
    saidas_por_ag = (sai
        .values("agulha__tipo", "agulha__tamanho")
        .annotate(total_sai=Sum("quantity_removed"))
    )

    resumo_map = {}
    for row in entradas_por_ag:
        k = (row["agulha__tipo"], row["agulha__tamanho"])
        resumo_map[k] = {
            "tipo": k[0], "tamanho": k[1],
            "entradas": row["total_ent"] or 0, "saidas": 0
        }
    for row in saidas_por_ag:
        k = (row["agulha__tipo"], row["agulha__tamanho"])
        if k not in resumo_map:
            resumo_map[k] = {
                "tipo": k[0], "tamanho": k[1],
                "entradas": 0, "saidas": row["total_sai"] or 0
            }
        else:
            resumo_map[k]["saidas"] = row["total_sai"] or 0

    resumo_por_agulha = []
    for v in resumo_map.values():
        v["saldo"] = v["entradas"] - v["saidas"]
        resumo_por_agulha.append(v)

    # ordenar por tipo e tamanho
    resumo_por_agulha.sort(key=lambda x: (x["tipo"], x["tamanho"]))

    users = User.objects.all().order_by("username")

    ctx = {
        "registos": historico,
        "filtro_data": filtro_data,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "user_id": int(user_id) if user_id.isdigit() else 0,
        "users": users,
        "tipo": tipo,

        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_total": total_entradas - total_saidas,
        "total_listado": total_listado,

        "resumo_por_agulha": resumo_por_agulha,
    }
    return render(request, "management/historico_agulhas.html", ctx)


def novo_stock(request):
    if request.method == 'POST':
        product = request.POST.get('product')
        min_stock = request.POST.get('min_stock') or '0'
        quantity_init = request.POST.get('quantity') or '0'
        fornecedor_id = request.POST.get('fornecedor')
        category_id = request.POST.get('category')

        try:
            fornecedor = Fornecedor.objects.get(id=fornecedor_id)
            category = CategoriaProduto.objects.get(id=category_id)
            qty_init_int = int(quantity_init) if str(quantity_init).isdigit() else 0
            Stock.objects.create(
                product=product,
                quantity=qty_init_int,
                min_stock=int(min_stock),
                fornecedor=fornecedor,
                user=request.user
            )
            messages.success(request, "Novo stock criado com sucesso.")
            return redirect('listar_stock')

        except Fornecedor.DoesNotExist:
            messages.error(request, "Fornecedor inválido.")
        except ValueError:
            messages.error(request, "Dados inválidos ao criar stock.")

    category = CategoriaProduto.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/novo_stock.html', {'fornecedor': fornecedor, 'category': category})

def nova_agulha(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        tamanho = request.POST.get('tamanho')
        quantidade_init = request.POST.get('quantidade') or '0'
        fornecedor_id = request.POST.get('fornecedor')

        try:
            fornecedor = Fornecedor.objects.get(id=fornecedor_id)
            qty_init_int = int(quantidade_init) if str(quantidade_init).isdigit() else 0
            Agulhas.objects.create(
                tipo=tipo,
                tamanho=tamanho,
                quantidade=qty_init_int,
                fornecedor=fornecedor,
                user=request.user
            )
            messages.success(request, "Nova agulha criada com sucesso.")
            return redirect('listar_agulhas')

        except Fornecedor.DoesNotExist:
            messages.error(request, "Fornecedor inválido.")
        except ValueError:
            messages.error(request, "Dados inválidos ao criar agulha.")

    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/nova_agulha.html', {'fornecedor': fornecedor})