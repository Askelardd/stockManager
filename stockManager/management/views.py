from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from django.urls import reverse
from django.utils.timezone import now, make_aware
from django.contrib.auth.models import User
from .models import Po, Fornecedor, StockEntradas, StockSaidas, UpdateStock, fioSaidas , updateFios, updatePo, CategoriaProduto, FioUsado, stockMaquinas
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
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings


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

def menu_fornecedor(request):
    return render(request, 'management/menu_fornecedor.html')

def menu_maquinas(request):
    return render(request, 'management/menu_maquinas.html')

def user_logout(request):
    logout(request)
    messages.success(request, "Saiu da sua conta com sucesso!")
    return redirect('index')

def error_403(request, exception=None):
    return render(request, '403.html', status=403)

def error_404(request, exception):
    return render(request, '404.html', status=404)


def stock_overview(request):
    return redirect('http://192.168.1.112:18000')

def login_view(request, user_id=None):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        password = request.POST.get('password', '')

        auth_user = authenticate(request, username=user.username, password=password)
        if auth_user is not None:
            auth_login(request, auth_user)  # cria a sessão
            messages.success(request, f'Bem-vindo, {auth_user.username}!')
            # PRG: redireciona para evitar repost em refresh
            return redirect('main_menu')  # ou outra página, por ex. 'listar_pos'
        else:
            messages.error(request, 'Palavra-passe inválida.')

    return render(request, 'management/login.html', {'user': user})

@login_required
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

        fornecedor = None
        if fornecedor_id:
            try:
                fornecedor = Fornecedor.objects.get(id=fornecedor_id)
            except Fornecedor.DoesNotExist:
                messages.error(request, "Fornecedor inválido.")
                return render(request, 'management/novo_fio.html', {
                    'fornecedores': fornecedores,
                    'material_choices': material_choices,
                    'form': request.POST,
                })

        # The following code block is commented out as it checks for the existence of a similar Fio
        # and prevents the creation of a duplicate. Uncomment if this behavior is desired.

        # existente = Fios.objects.filter(
        #     material=material,
        #     size=size
        # ).first()

        # if existente:
        #     messages.info(request, f"O Fio {existente.size}mm com o material {existente.material} já existe.")
        #     return render(request, 'management/novo_fio.html', {
        #         'fornecedores': fornecedores,
        #         'material_choices': material_choices,
        #         'form': request.POST,
        #     })

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
                raise InvalidOperation("Quantidade/Stock mínimo não podem ser negativos.")

            weight_unit = weight_dec / quantity_int if quantity_int > 0 else Decimal('0')  # Calcula weight_unit

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
            weight_unit=weight_unit,
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

@login_required
def listar_pos(request):
    pos = Po.objects.all()
    fornecedor = Fornecedor.objects.all()
    filtro_data = request.GET.get('filtro_data')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Atualização via POST (incrementar/decrementar quantidade)
    if request.method == 'POST':
        po_id = request.POST.get('po_id')
        po_item = get_object_or_404(Po, id=po_id)

        if 'increment' in request.POST:

            
            prev_quantity = po_item.quantity
            po_item.quantity += 1
            stock_after_addition = po_item.quantity 
            action = 'added'

        elif 'decrement' in request.POST:
            prev_quantity = po_item.quantity
            po_item.quantity -= 1
            stock_after_use = po_item.quantity
            action = 'removed'
            print("Decrementing PO:", po_item.id)

        else:
            action = None

        if action:
            po_item.user = request.user
            po_item.save()

            # Criar registo de entrada/saída com previous_quantity
            if action == 'added':
                poEntradas.objects.create(
                    po=po_item,
                    quantity_added=1,
                    previous_quantity=prev_quantity,
                    stock_after_addition= stock_after_addition,
                    user=request.user
                )

            elif action == 'removed':
                poSaidas.objects.create(
                    po=po_item,
                    quantity_used=1,
                    previous_quantity=prev_quantity,
                    stock_after_use= stock_after_use,
                    user=request.user
                )

                # Alerta stock mínimo
                if po_item.quantity < po_item.min_stock:
                    messages.warning(
                        request, 
                        f"Atenção: A quantidade do PO '{po_item.reference}' está abaixo do Stock mínimo!"
                    )
                    send_mail(
                        subject="Alerta de Stock Mínimo para PO",
                        message=f"O Stock do PO '{po_item.reference}' caiu abaixo do mínimo definido ({po_item.min_stock}). Quantidade atual: {po_item.quantity}.",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=settings.EMAIL_RECIPIENTS,
                        fail_silently=False,
                    )

        return redirect('listar_pos')

    return render(request, 'management/listar_pos.html', {
        'pos': pos,
        'fornecedor': fornecedor,
        'filtro_data': filtro_data,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })

@login_required
def adicionarMaisde1Po(request, po_id):
    po = get_object_or_404(Po, pk=po_id)

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            previous_quantity = po.quantity
            po.quantity += quantidade
            stock_after_addition = po.quantity
            po.user = request.user
            po.save()

            # Registo direto de entrada com previous_quantity
            poEntradas.objects.create(
                po=po,
                quantity_added=quantidade,
                previous_quantity=previous_quantity,
                stock_after_addition=stock_after_addition,
                user=request.user
            )

            return redirect('listar_pos')

        except ValueError:
            context = {'po': po, 'error': "Por favor, insira um número válido maior que zero."}
            return render(request, 'management/adicionar_po.html', context)

    return render(request, 'management/adicionar_po.html', {'po': po})


@login_required
def removerPo(request, po_id):
    po = get_object_or_404(Po, pk=po_id)
    context = {'po': po}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            previous_quantity = po.quantity
            po.quantity -= quantidade
            stock_after_use = po.quantity
            po.user = request.user
            po.save()

            # Registo direto de saída com previous_quantity
            poSaidas.objects.create(
                po=po,
                quantity_used=quantidade,
                stock_after_use=stock_after_use,
                previous_quantity=previous_quantity,
                user=request.user
            )

            if po.quantity < po.min_stock:
                messages.warning(
                    request,
                    f"Atenção: A quantidade do PO '{po.reference}' está abaixo do Stock mínimo!"
                )
                context['warning'] = True

                send_mail(
                    subject="Alerta de Stock Mínimo para PO",
                    message=f"O Stock do PO '{po.reference}' caiu abaixo do mínimo definido ({po.min_stock}). Quantidade atual: {po.quantity}.",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=settings.EMAIL_RECIPIENTS,
                    fail_silently=False,
                )

            context['success'] = True
            return redirect('listar_pos')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."

    return render(request, 'management/remover_po.html', context)


@login_required
def historico_po(request):
    filtro_data = request.GET.get("filtro_data", "hoje")
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    user_id = request.GET.get("user_id", "0")
    tipo = request.GET.get("tipo", "todos")  # "todos" | "entradas" | "saidas"
    ref = (request.GET.get("ref") or "").strip()

    di, df = _range_por_filtro(filtro_data, data_inicio, data_fim)

    # 🔹 Base querysets com filtros de tempo
    ent = poEntradas.objects.select_related("po", "user").filter(date_added__range=(di, df))
    sai = poSaidas.objects.select_related("po", "user").filter(date_used__range=(di, df))

    # 🔹 Filtro por utilizador
    if user_id and user_id.isdigit() and int(user_id) != 0:
        ent = ent.filter(user__id=int(user_id))
        sai = sai.filter(user__id=int(user_id))

    # 🔹 Filtro por referência
    refs_ent = set(ent.values_list("po__reference", flat=True).distinct())
    refs_sai = set(sai.values_list("po__reference", flat=True).distinct())
    refs_disponiveis = sorted((refs_ent | refs_sai) - {None, ""})

    if ref:
        ent = ent.filter(po__reference=ref)
        sai = sai.filter(po__reference=ref)

    # 🔹 Normalizar ENTRADAS
    ent_norm = ent.annotate(
        date=F("date_added"),
        quantity=F("quantity_added"),
        direction=Value("entrada", output_field=CharField()),
        po_product=F("po__product"),
        po_reference=F("po__reference"),
        previous_stock=F("previous_quantity"),
        stock_after_movement=F("stock_after_addition"),
        username=F("user__username"),
    ).values(
        "date", "quantity", "direction", "po_product", "po_reference",
        "previous_stock", "stock_after_movement", "username"
    )

    # 🔹 Normalizar SAÍDAS
    sai_norm = sai.annotate(
        date=F("date_used"),
        quantity=F("quantity_used"),
        direction=Value("saida", output_field=CharField()),
        po_product=F("po__product"),
        po_reference=F("po__reference"),
        previous_stock=F("previous_quantity"),
        stock_after_movement=F("stock_after_use"),
        username=F("user__username"),
    ).values(
        "date", "quantity", "direction", "po_product", "po_reference",
        "previous_stock", "stock_after_movement", "username"
    )

    # 🔹 União e ordenação
    if tipo == "entradas":
        historico = ent_norm
    elif tipo == "saidas":
        historico = sai_norm
    else:
        historico = ent_norm.union(sai_norm, all=True)

    historico = historico.order_by("-date")

    # 🔹 Totais
    total_entradas = ent.aggregate(total=Sum("quantity_added"))["total"] or 0
    total_saidas = sai.aggregate(total=Sum("quantity_used"))["total"] or 0
    total_listado = total_entradas if tipo == "entradas" else (total_saidas if tipo == "saidas" else None)

    # 🔹 Resumo por PO
    entradas_por_po = ent.values("po__product", "po__reference").annotate(total_ent=Sum("quantity_added"))
    saidas_por_po = sai.values("po__product", "po__reference").annotate(total_sai=Sum("quantity_used"))
    existentes = Po.objects.filter(quantity__gt=0).values("product", "reference").annotate(total=Sum("quantity"))

    resumo_map = {}
    for row in entradas_por_po:
        key = (row["po__product"], row["po__reference"])
        resumo_map[key] = {
            "product": key[0],
            "reference": key[1],
            "entradas": row["total_ent"] or 0,
            "saidas": 0,
            "existentes": 0
        }

    for row in saidas_por_po:
        key = (row["po__product"], row["po__reference"])
        if key not in resumo_map:
            resumo_map[key] = {
                "product": key[0],
                "reference": key[1],
                "entradas": 0,
                "saidas": row["total_sai"] or 0,
                "existentes": 0
            }
        else:
            resumo_map[key]["saidas"] = row["total_sai"] or 0

    for row in existentes:
        key = (row["product"], row["reference"])
        if key in resumo_map:
            resumo_map[key]["existentes"] = row["total"] or 0

    resumo_por_po = []
    for v in resumo_map.values():
        v["saldo"] = (v["entradas"] or 0) - (v["saidas"] or 0)
        resumo_por_po.append(v)

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
        "ref": ref,
        "refs_disponiveis": refs_disponiveis,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_total": total_entradas - total_saidas,
        "total_listado": total_listado,
        "existentes": existentes,
        "resumo_por_po": resumo_por_po,
    }
    return render(request, "management/historico_po.html", ctx)



@login_required
def listar_updates(request):
    updates = updatePo.objects.all()
    return render(request, 'management/listar_update_pos.html', {'updates': updates})


@login_required
def listar_fiousado(request):
    fios_usados = FioUsado.objects.all()
    return render(request, 'management/listar_fiousado.html', {'fios_usados': fios_usados})


@login_required
def deletar_fiousado(request, id):  # <— bate com a URL
    fio_usado = get_object_or_404(FioUsado, pk=id)

    if request.method == 'POST':
        if fio_usado.quantidade_usada > 1:
            fio_usado.quantidade_usada -= 1
            fio_usado.save()
            messages.success(request, "Quantidade de fio usado decrementada com sucesso.")
        else:
            fio_usado.delete()
            messages.success(request, "Registro de fio usado deletado com sucesso.")

        return redirect('listar_fiousado')  
    return render(request, 'management/delecao_fiousado.html', {'fio_usado': fio_usado})


@login_required
def listar_fios(request):
    if request.method == 'POST':
        fio_id = request.POST.get('fio_id')
        if fio_id:
            fio_item = Fios.objects.get(id=fio_id)
            if 'increment' in request.POST:

                previous_quantity = fio_item.quantity
                fio_item.quantity += 1
                stock_after_use = fio_item.quantity
                fio_item.weight += fio_item.weight_unit


            elif 'decrement' in request.POST:
                previous_quantity = fio_item.quantity
                fio_item.quantity -= 1
                stock_after_use = fio_item.quantity

                fio_item.weight -= fio_item.weight_unit

                fio_usado = FioUsado.objects.filter(
                    fio=fio_item,
                    size=fio_item.size,
                    material=fio_item.material
                ).first()

                if fio_usado:
                    fio_usado.quantidade_usada += 1
                    fio_usado.save()
                else:
                    FioUsado.objects.create(
                        fio=fio_item,
                        size=fio_item.size,
                        weight=fio_item.weight_unit,
                        material=fio_item.material,
                        quantidade_usada=1,
                        stock_after_use= stock_after_use,
                        data_uso=now(),
                        user=request.user
                    )

            updateFios.objects.create(
                fio=fio_item,
                previous_quantity=fio_item.quantity - (1 if 'increment' in request.POST else -1),
                stock_after_use=stock_after_use,
                new_quantity=fio_item.quantity,
                user=request.user,
                action='added' if 'increment' in request.POST else 'removed'
            )

            fio_item.save()
            fio_item.user = request.user
            fio_item.save()

            if fio_item.quantity == 0:
                fio_item.weight = 0


        return redirect('listar_fios')

    fios = Fios.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/listar_fios.html', {'fios': fios, 'fornecedor': fornecedor})

@login_required
def adicionarMaisde1Fio(request, fio_id):
    fio = get_object_or_404(Fios, pk=fio_id)
    context = {'fio': fio}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            previous_quantity = fio.quantity
            fio.quantity += quantidade
            stock_after_use = fio.quantity
            fio.user = request.user
            fio.weight += fio.weight_unit * quantidade

            fio.save()

            fio_usado = FioUsado.objects.filter(
                fio=fio,
                size=fio.size,
                material=fio.material
            ).first()

            if fio_usado:
                fio_usado.quantidade_usada += 1
                fio_usado.save()
            else:
                FioUsado.objects.create(
                    fio=fio,
                    size=fio.size,
                    weight=fio.weight_unit,
                    material=fio.material,
                    quantidade_usada=1,
                    stock_after_use=stock_after_use,
                    data_uso=now(),
                    user=request.user
                )

            update_fio = updateFios(
                fio=fio,
                previous_quantity=fio.quantity - quantidade,
                stock_after_use=stock_after_use,
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

def editar_fio(request, fio_id):
    fio = get_object_or_404(Fios, pk=fio_id)

    # 🟢 Converter valores ANTES de mostrar no formulário
    fio.weight = str(fio.weight).replace(',', '.')
    fio.weight_unit = str(fio.weight_unit).replace(',', '.')

    context = {'fio': fio}

    if request.method == 'POST':
        peso = request.POST.get('peso')
        quantidade = request.POST.get('quantidade', '0')
        peso_unit = request.POST.get('peso_unit', '0')
        min_stock = request.POST.get('min_stock', '0')

        # 🟢 Convertendo vírgulas enviadas pelo user também
        peso = peso.replace(',', '.')
        peso_unit = peso_unit.replace(',', '.')

        try:
            peso_dec = Decimal(peso.strip()) if peso.strip() else Decimal('0')
            quantidade_int = int(quantidade.strip()) if quantidade.strip() else 0
            peso_unit_dec = Decimal(peso_unit.strip()) if peso_unit.strip() else Decimal('0')
        except (InvalidOperation, ValueError):
            messages.error(request, "Por favor, insira valores numéricos válidos para peso, quantidade e peso unitário.")
            return redirect(request.path)

        if peso_dec < 0 or quantidade_int < 0 or peso_unit_dec < 0:
            messages.error(request, "Valores não podem ser negativos.")
            return redirect(request.path)

        if quantidade_int == 0:
            quantidade_int = int(request.POST.get('quantidade_atual', fio.quantity))

        if peso_unit == '0' or peso_unit.strip() == '':
            peso_unit_dec = peso_dec / quantidade_int if quantidade_int > 0 else Decimal('0')

        fio.weight = peso_dec
        fio.quantity = quantidade_int
        fio.weight_unit = peso_unit_dec
        fio.user = request.user
        fio.min_stock = int(min_stock)
        fio.save()

        messages.success(request, "Fio atualizado com sucesso!")
        return redirect('listar_fios')

    return render(request, 'management/editar_fio.html', context)


def retirar_fio(request, fio_id):
    fio = get_object_or_404(Fios, pk=fio_id)

    if request.method == 'POST':
        peso = request.POST.get('Peso', '').strip()  

        if not peso:
            messages.error(request, "O campo 'Peso' é obrigatório.")
            return redirect(request.path)

        try:
            peso_dec = Decimal(peso)
        except InvalidOperation:
            messages.error(request, "Valor de peso inválido.")
            return redirect(request.path)
        
        try:
            new_weight_unit = (fio.weight - peso_dec) / (fio.quantity - 1) if (fio.quantity - 1) > 0 else Decimal('0')
        except InvalidOperation:
            messages.error(request, "Operação inválida ao calcular peso unitário.")
            return redirect(request.path)
        
        try:
            if fio.quantity > 0:
                fio.weight = fio.weight - peso_dec
                fio.weight_unit = new_weight_unit
                fio.quantity -= 1
                fio.user = request.user
                fio.save()

            FioUsado.objects.create(
                fio=fio,
                size=fio.size,
                weight=peso_dec,
                material=fio.material,
                quantidade_usada=1,
                stock_after_use=fio.quantity,
                data_uso=now(),
                user=request.user
            )
            messages.success(request, "Fio retirado com sucesso!")
            return redirect('listar_fios')

        except InvalidOperation:
            messages.error(request, "Valor de peso inválido.")
            return redirect(request.path)

    return render(request, 'management/retirar_fio.html', {'fio': fio})

@login_required
def listar_updates_fios(request):
    updates = updateFios.objects.all()
    return render(request, 'management/listar_update_fios.html', {'updates': updates})

@login_required
def historico_fios(request):
    filtro_data = request.GET.get("filtro_data", "hoje")
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    user_id = request.GET.get("user_id", "0")
    tipo = request.GET.get("tipo", "todos")  # "todos" | "entradas" | "saidas"
    incluir_legacy = request.GET.get("incluir_legacy") == "1"
    tamanho = request.GET.get("tamanho", None)  # Filtro por tamanho

    di, df = _range_por_filtro(filtro_data, data_inicio, data_fim)

    upd = updateFios.objects.select_related("fio", "user").filter(date_updated__range=(di, df))
    if user_id.isdigit() and int(user_id) != 0:
        upd = upd.filter(user__id=int(user_id))
    if tamanho:
        upd = upd.filter(fio__size=tamanho)

    # 🔹 ENTRADAS
    upd_add = upd.filter(action="added").annotate(
        date=F("date_updated"),
        quantity=F("new_quantity") - F("previous_quantity"),
        direction=Value("entrada", output_field=CharField()),
        fio_size=F("fio__size"),
        fio_weight=F("fio__weight"),
        fio_material=F("fio__material"),
        previous_stock=F("previous_quantity"),
        stock_after_movement=F("new_quantity"),
        current_stock=F("fio__quantity"),
        username=F("user__username"),
    ).values(
        "date", "quantity", "direction", "fio_size", "fio_weight", "fio_material",
        "previous_stock", "stock_after_movement", "current_stock", "username"
    )

    # 🔹 SAÍDAS
    upd_rem = upd.filter(action="removed").annotate(
        date=F("date_updated"),
        quantity=F("previous_quantity") - F("new_quantity"),
        direction=Value("saida", output_field=CharField()),
        fio_size=F("fio__size"),
        fio_weight=F("fio__weight"),
        fio_material=F("fio__material"),
        previous_stock=F("previous_quantity"),
        stock_after_movement=F("new_quantity"),
        current_stock=F("fio__quantity"),
        username=F("user__username"),
    ).values(
        "date", "quantity", "direction", "fio_size", "fio_weight", "fio_material",
        "previous_stock", "stock_after_movement", "current_stock", "username"
    )

    # 🔹 LEGACY SAÍDAS
    legacy_norm = None
    if incluir_legacy:
        legacy = fioSaidas.objects.select_related("fio", "user").filter(date_used__range=(di, df))
        if user_id.isdigit() and int(user_id) != 0:
            legacy = legacy.filter(user__id=int(user_id))
        if tamanho:
            legacy = legacy.filter(fio__size=tamanho)
        legacy_norm = legacy.annotate(
            date=F("date_used"),
            quantity=F("quantity_used"),
            direction=Value("saida", output_field=CharField()),
            fio_size=F("fio__size"),
            fio_weight=F("fio__weight"),
            fio_material=F("fio__material"),
            previous_stock=F("previous_quantity"),
            stock_after_movement=F("stock_after_use"),
            current_stock=F("fio__quantity"),
            username=F("user__username"),
        ).values(
            "date", "quantity", "direction", "fio_size", "fio_weight", "fio_material",
            "previous_stock", "stock_after_movement", "current_stock", "username"
        )

    # 🔹 Filtrar tipo e unir
    if tipo == "entradas":
        historico = upd_add
    elif tipo == "saidas":
        historico = upd_rem if not legacy_norm else upd_rem.union(legacy_norm, all=True)
    else:
        historico = upd_add.union(upd_rem, all=True)
        if legacy_norm:
            historico = historico.union(legacy_norm, all=True)

    historico = historico.order_by("-date")

    # 🔹 Totais
    total_entradas = upd_add.aggregate(total=Sum("quantity"))["total"] or 0
    total_saidas = upd_rem.aggregate(total=Sum("quantity"))["total"] or 0
    if incluir_legacy and legacy_norm:
        total_saidas += legacy.aggregate(total=Sum("quantity_used"))["total"] or 0

    total_listado = total_entradas if tipo == "entradas" else (total_saidas if tipo == "saidas" else None)
    existencias = (Fios.objects
                .values("size", "weight", "material")
                .annotate(total_exist=Sum("quantity")))

    # criar um dicionário para lookup rápido
    exist_map = {}
    for row in existencias:
        key = (row["size"], row["weight"], row["material"])
        exist_map[key] = row["total_exist"] or 0

    # 🔹 Resumo
    resumo_map = {}
    for row in upd_add:
        k = (row["fio_size"], row["fio_weight"], row["fio_material"])
        resumo_map[k] = {"size": k[0], "weight": k[1], "material": k[2],
                        "entradas": row["quantity"], "saidas": 0,
                        "existencias": exist_map.get(k, 0)}

    for row in upd_rem:
        k = (row["fio_size"], row["fio_weight"], row["fio_material"])
        if k not in resumo_map:
            resumo_map[k] = {"size": k[0], "weight": k[1], "material": k[2],
                            "entradas": 0, "saidas": row["quantity"],
                            "existencias": exist_map.get(k, 0)}
        else:
            resumo_map[k]["saidas"] += row["quantity"]

    if incluir_legacy and legacy_norm:
        for row in legacy_norm:
            k = (row["fio_size"], row["fio_weight"], row["fio_material"])
            if k not in resumo_map:
                resumo_map[k] = {"size": k[0], "weight": k[1], "material": k[2],
                                "entradas": 0, "saidas": row["quantity"],
                                "existencias": exist_map.get(k, 0)}
            else:
                resumo_map[k]["saidas"] += row["quantity"]

    # 🔹 Criar lista final
    resumo_por_fio = []
    for v in resumo_map.values():
        v["saldo"] = (v["existencias"] or 0) + (v["entradas"] or 0) - (v["saidas"] or 0)
        resumo_por_fio.append(v)

    resumo_por_fio.sort(key=lambda x: (x["material"], x["size"], x["weight"]))

    users = User.objects.all().order_by("username")
    tamanhos = Fios.objects.values_list('size', flat=True).distinct().order_by('size')

    ctx = {
        "registos": historico,
        "filtro_data": filtro_data,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "user_id": int(user_id) if user_id.isdigit() else 0,
        "users": users,
        "tamanhos": tamanhos,
        "tamanho_selecionado": tamanho,  # Para manter o tamanho selecionado no filtro
        "tipo": tipo,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_total": total_entradas - total_saidas,
        "total_listado": total_listado,
        "resumo_por_fio": resumo_por_fio,
        "incluir_legacy": incluir_legacy,
    }
    return render(request, "management/historico_fios.html", ctx)


@login_required
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


@login_required
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



@login_required
def trafilar_fio(request):

    origem_usado_id = request.GET.get('origem_usado_id') or request.POST.get('origem_usado_id')
    origem_usado = get_object_or_404(FioUsado, id=origem_usado_id) if origem_usado_id else None

    # Lista para escolher a origem
    usados_lista = FioUsado.objects.order_by('-data_uso', '-id')

    # Destinos filtrados pelo material do FioUsado
    destinos_qs = Fios.objects.none()
    origem_ppb = None
    if origem_usado:
        destinos_qs = Fios.objects.filter(material=origem_usado.material).order_by('size')
        try:
            if origem_usado.quantidade_usada:
                # PPB: peso por bobine do lote de origem (2 casas decimais)
                origem_ppb = (Decimal(origem_usado.weight) / Decimal(origem_usado.quantidade_usada)).quantize(Decimal('0.01'))
        except (InvalidOperation, ZeroDivisionError):
            origem_ppb = None

    if request.method == 'POST':
        if not origem_usado:
            messages.error(request, "Selecione um lote (FioUsado) de origem.")
            return redirect('trafilar_fio')

        quantidade_str = request.POST.get('quantidade') or '0'
        pesos_bobine = [p for p in request.POST.getlist('peso_bobine[]') if str(p).strip() != '']
        target_ids = request.POST.getlist('target_id[]')
        weights    = request.POST.getlist('peso[]')

        # --- validação quantidade ---
        try:
            qtd_bobines = int(quantidade_str)
        except (TypeError, ValueError):
            qtd_bobines = 0
        if qtd_bobines <= 0:
            messages.error(request, "Informe a quantidade de bobines a usar (maior que zero).")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")
        if qtd_bobines > (origem_usado.quantidade_usada or 0):
            messages.error(request, f"A quantidade ({qtd_bobines}) excede o stock disponível ({origem_usado.quantidade_usada}).")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

        # --- PPB da origem (limite por bobine) ---
        if not origem_ppb or origem_ppb <= 0:
            messages.error(request, "Não foi possível calcular o peso por bobine (PPB) da origem.")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

        # precisam existir exatamente N pesos de bobine
        if len(pesos_bobine) != qtd_bobines:
            messages.error(request, f"Indique o peso a trefilar para cada uma das {qtd_bobines} bobines.")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

        # valida pesos por bobine e separa integrais vs parciais
        pesos_bobine_dec = []
        full_consumed = 0
        partial_remainders = []  # lista de Decimal (peso remanescente por bobine parcial)
        try:
            for p in pesos_bobine:
                val = Decimal(p).quantize(Decimal('0.01'))
                if val <= 0:
                    raise ValueError("Peso por bobine deve ser > 0.")
                if val > origem_ppb:
                    raise ValueError(f"Peso por bobine ({val} g) excede o máximo por bobine ({origem_ppb} g).")

                pesos_bobine_dec.append(val)

                if val == origem_ppb:
                    full_consumed += 1
                else:
                    partial_remainders.append((origem_ppb - val).quantize(Decimal('0.01')))
        except (InvalidOperation, ValueError) as e:
            messages.error(request, f"Erro nos pesos por bobine: {e}")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

        total_por_bobines = sum(pesos_bobine_dec, Decimal('0')).quantize(Decimal('0.01'))

        # --- destinos (mesma lógica de antes) ---
        pares = []
        for tid, w in zip(target_ids, weights):
            if (not tid or tid.strip() == '') and (not w or w.strip() == ''):
                continue
            pares.append((tid.strip(), w.strip()))
        if not pares:
            messages.error(request, "Adicione pelo menos um destino e um peso.")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

        vistos = {}
        total_destinos = Decimal('0')
        try:
            for tid, w in pares:
                if not tid:
                    raise ValueError("Selecione um destino (medida).")
                destino_fio = Fios.objects.get(id=tid)

                if destino_fio.material != origem_usado.material:
                    raise ValueError("Material do destino deve ser igual ao da origem (FioUsado).")

                peso = Decimal(w).quantize(Decimal('0.01'))
                if peso <= 0:
                    raise ValueError("Peso do destino deve ser maior que zero.")

                key = f"{destino_fio.id}"
                if key in vistos:
                    vistos[key] += peso
                else:
                    vistos[key] = peso

            total_destinos = sum(vistos.values(), Decimal('0')).quantize(Decimal('0.01'))
        except (Fios.DoesNotExist, InvalidOperation, ValueError) as e:
            messages.error(request, f"Erro de validação dos destinos: {e}")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

        # totais têm de bater e não exceder o disponível
        if total_destinos != total_por_bobines:
            messages.error(request, f"O total distribuído ({total_destinos} g) deve ser igual ao total retirado ({total_por_bobines} g).")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")
        if total_por_bobines > origem_usado.weight:
            messages.error(request, f"Peso a retirar ({total_por_bobines} g) excede o disponível ({origem_usado.weight} g).")
            return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

        # --- TRANSACÃO ---
        with transaction.atomic():
            peso_antes = origem_usado.weight
            qtd_antes  = origem_usado.quantidade_usada

            # 1) Debita na origem: remove TODAS as bobines usadas (inteiras + parciais)
            #    - Peso: PPB * qtd_bobines
            debito_peso_total = (origem_ppb * Decimal(qtd_bobines)).quantize(Decimal('0.01'))
            origem_usado.weight = F('weight') - debito_peso_total
            origem_usado.quantidade_usada = F('quantidade_usada') - qtd_bobines
            origem_usado.user = request.user
            origem_usado.save(update_fields=['weight', 'quantidade_usada', 'user'])
            origem_usado.refresh_from_db(fields=['weight', 'quantidade_usada'])

            # 2) Criar FioUsado(s) remanescentes para bobines PARCIAIS
            remanescentes = []
            for rem in partial_remainders:  # rem = PPB - retirado
                if rem > 0:
                    remanescentes.append(FioUsado(
                        fio=origem_usado.fio,
                        size=origem_usado.size,
                        weight=rem,
                        material=origem_usado.material,
                        quantidade_usada=1,
                        data_uso=timezone.now(),
                        user=request.user
                    ))
            if remanescentes:
                FioUsado.objects.bulk_create(remanescentes)

            # 3) Log principal (referencia o Fio “pai” do lote)
            transf = FioTransformacao.objects.create(
                origem=origem_usado.fio,
                total_transferido=total_por_bobines,
                peso_origem_antes=peso_antes,
                peso_origem_depois=origem_usado.weight + sum((r.weight for r in remanescentes), Decimal('0')) if remanescentes else origem_usado.weight,
                user=request.user
            )

            # 4) Para cada destino: cria FioUsado produzido
            produzidos = []
            for dest_id, peso_add in vistos.items():
                destino_fio = Fios.objects.get(id=dest_id)

                # log item (opcional, mantém histórico do Fio destino)
                FioTransformacaoItem.objects.create(
                    transformacao=transf,
                    destino=destino_fio,
                    peso_adicionado=peso_add
                )

                # cria o lote produzido (1 unidade; se quiseres podemos agregar por destino)
                produzidos.append(FioUsado(
                    fio=destino_fio,
                    size=destino_fio.size,
                    weight=peso_add,
                    material=destino_fio.material,
                    quantidade_usada=1,
                    data_uso=timezone.now(),
                    user=request.user
                ))
            if produzidos:
                FioUsado.objects.bulk_create(produzidos)

        # resumo
        msg_extra = ""
        if partial_remainders:
            msg_extra = f" · Criadas {len(partial_remainders)} bobine(s) remanescentes."
        messages.success(
            request,
            f"Trefilagem concluída. Retirado {total_por_bobines} g de {qtd_bobines} bobine(s)."
            f"{msg_extra} Após operação: origem → {origem_usado.weight} g · Qtd: {origem_usado.quantidade_usada}."
        )
        return redirect(f"{request.path}?origem_usado_id={origem_usado.id}")

    # GET
    context = {
        'origem_usado': origem_usado,
        'origem_ppb': origem_ppb,
        'usados_lista': usados_lista,
        'destinos': destinos_qs,
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
        fornecedor = Fornecedor.objects.get(id=fornecedor_id) if fornecedor_id else None
        size = Decimal(size_str)
        if size <= 0:
            raise InvalidOperation("Tamanho inválido.")

        existente = Fios.objects.filter(
            material=origem.material,
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



@login_required
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


@login_required
def listar_stock(request):
    if request.method == 'POST':
        stock_id = request.POST.get('stock_id')
        if stock_id:
            stock_item = Stock.objects.get(id=stock_id)
            if 'increment' in request.POST:
                previous_quantity = stock_item.quantity
                stock_item.quantity += 1
                stock_after_added = stock_item.quantity
                

                update_stock = UpdateStock.objects.create(
                    stock=stock_item,
                    previous_quantity=stock_item.quantity - 1,
                    new_quantity=stock_item.quantity,
                    stock_after_use=stock_after_added,
                    action='added',
                    user=request.user
                )

                StockEntradas.objects.create(
                    stock=stock_item,
                    quantity_added=1,
                    previous_quantity=previous_quantity,
                    stock_after_added=stock_after_added,
                    user=request.user
                )

            elif 'decrement' in request.POST:
                previous_quantity = stock_item.quantity
                stock_item.quantity -= 1
                stock_after_use = stock_item.quantity

                update_stock = UpdateStock.objects.create(
                    stock=stock_item,
                    new_quantity=stock_item.quantity,
                    previous_quantity=previous_quantity,
                    stock_after_use=stock_after_use,
                    action='removed',
                    user=request.user
                )

                if stock_item.quantity < stock_item.min_stock:
                    messages.warning(request, f"O Stock do '{stock_item.product}' caiu abaixo do mínimo definido ({stock_item.min_stock}). Quantidade atual: {stock_item.quantity}.")

                    send_mail(
                        subject="Alerta de Stock Mínimo para Stock",
                        message=f"O Stock do '{stock_item.product}' caiu abaixo do mínimo definido ({stock_item.min_stock}). Quantidade atual: {stock_item.quantity}.",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=settings.EMAIL_RECIPIENTS,
                        fail_silently=False,
                        )
                
                StockSaidas.objects.create(
                    stock=stock_item,
                    quantity_removed=1,
                    previous_quantity=previous_quantity,
                    stock_after_use=stock_after_use,
                    user=request.user
                )

                

            stock_item.save()
            stock_item.user = request.user
            stock_item.save()

        return redirect('listar_stock')

    stock = Stock.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/listar_stock.html', {'stock': stock, 'fornecedor': fornecedor})

@login_required
def adicionarStock(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            descricao = request.POST.get('descricao_field', '').strip()
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            previous_quantity = stock.quantity
            stock.quantity += quantidade
            stock_after_added = stock.quantity
            stock.user = request.user
            stock.save()

            UpdateStock.objects.create(
                stock=stock,
                previous_quantity= previous_quantity,
                new_quantity=stock.quantity,
                action='added',
                user=request.user
            )
            
            StockEntradas.objects.create(
                stock=stock,
                quantity_added=quantidade,
                previous_quantity=previous_quantity,
                descricao=descricao,
                stock_after_added=stock_after_added,
                user=request.user
            )

            return redirect('listar_stock')

        except ValueError:
            context = {'stock': stock, 'error': "Por favor, insira um número válido maior que zero."}
            return render(request, 'management/adicionar_stock.html', context)

    return render(request, 'management/adicionar_stock.html', {'stock': stock})

@login_required
def removerStock(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)
    context = {'stock': stock}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            descricao = request.POST.get('descricao_field', '').strip()
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            previous_quantity = stock.quantity
            stock.quantity -= quantidade
            stock.user = request.user
            stock_after_use = stock.quantity
            stock.save()

            UpdateStock.objects.create(
                stock=stock,
                previous_quantity=previous_quantity,
                new_quantity=stock.quantity,
                action='removed',
                user=request.user
            )

            StockSaidas.objects.create(
                stock=stock,
                quantity_removed=quantidade,
                previous_quantity=previous_quantity,
                descricao=descricao,
                stock_after_use=stock_after_use,
                user=request.user
            )

            context['success'] = True

            if stock.quantity < stock.min_stock:
                messages.warning(request, f"O Stock do '{stock.product}' caiu abaixo do mínimo definido ({stock.min_stock}). Quantidade atual: {stock.quantity}.")
                send_mail(
                    subject="Alerta de Stock Mínimo para Stock",
                    message=f"O Stock do '{stock.product}' caiu abaixo do mínimo definido ({stock.min_stock}). Quantidade atual: {stock.quantity}.",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=settings.EMAIL_RECIPIENTS,
                    fail_silently=False,
                    )

            return redirect('listar_stock')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."

    return render(request, 'management/remover_stock.html', context)



@login_required
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
            prev_quantity=F("previous_quantity"),
            stock_after_movement =F("stock_after_added"),
            categoria_nome=F("stock__categoria__nome"),
            descricao_field=F("descricao"),
        )
        .values("date", "quantity", "direction", "stock_product", "current_stock", "prev_quantity", "stock_after_movement", "categoria_nome", "descricao_field")
    )

    sai_norm = (sai
        .annotate(
            date=F("date_removed"),
            quantity=F("quantity_removed"),
            direction=Value("saida", output_field=CharField()),
            stock_product=F("stock__product"),
            categoria_nome=F("stock__categoria__nome"),
            current_stock=F("stock__quantity"),
            prev_quantity=F("previous_quantity"),
            stock_after_movement =F("stock_after_use"),
            descricao_field=F("descricao"),
        )
        .values("date", "quantity", "direction", "stock_product", "current_stock", "prev_quantity", "stock_after_movement", "categoria_nome", "descricao_field")
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

    # 🔹 Existências atuais por produto
    existencias = Stock.objects.all().values("product").annotate(total_exist=Sum("quantity"))

    # criar um dicionário para lookup rápido
    exist_map = {row["product"]: row["total_exist"] or 0 for row in existencias}

    # 🔹 Resumo por produto
    resumo_map = {}
    for row in entradas_por_prod:
        k = row["stock__product"]
        resumo_map[k] = {
            "product": k,
            "entradas": row["total_ent"] or 0,
            "saidas": 0,
            "existencias": exist_map.get(k, 0),
        }

    for row in saidas_por_prod:
        k = row["stock__product"]
        if k not in resumo_map:
            resumo_map[k] = {
                "product": k,
                "entradas": 0,
                "saidas": row["total_sai"] or 0,
                "existencias": exist_map.get(k, 0),
            }
        else:
            resumo_map[k]["saidas"] = row["total_sai"] or 0

    # 🔹 Criar lista final com saldo
    resumo_por_stock = []
    for v in resumo_map.values():
        v["saldo"] = (v["existencias"] or 0) + (v["entradas"] or 0) - (v["saidas"] or 0)
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

@login_required
def listar_agulhas(request):
    if request.method == 'POST':
        agulha_id = request.POST.get('agulha_id')
        if agulha_id:
            agulha_item = Agulhas.objects.get(id=agulha_id)
            if 'increment' in request.POST:
                previous_quantity = agulha_item.quantidade
                agulha_item.quantidade += 1
                stock_after_use = agulha_item.quantidade

                UpdateAgulhas.objects.create(
                    agulha=agulha_item,
                    previous_quantity=previous_quantity,
                    new_quantity=agulha_item.quantidade,
                    action='added',
                    user=request.user
                )

                AgulhasEntradas.objects.create(
                    agulha=agulha_item,
                    previous_quantity=previous_quantity,
                    quantity_added=1,
                    stock_after_use=stock_after_use,
                    user=request.user
                )
            elif 'decrement' in request.POST:
                previous_quantity = agulha_item.quantidade
                agulha_item.quantidade -= 1
                stock_after_use = agulha_item.quantidade

                UpdateAgulhas.objects.create(
                    agulha=agulha_item,
                    previous_quantity=previous_quantity,
                    new_quantity=agulha_item.quantidade,
                    action='removed',
                    user=request.user
                )

                AgulhasSaidas.objects.create(
                    agulha=agulha_item,
                    previous_quantity=previous_quantity,
                    quantity_removed=1,
                    stock_after_use=stock_after_use,
                    user=request.user
                )

            agulha_item.save()
            agulha_item.user = request.user
            agulha_item.save()

        return redirect('listar_agulhas')

    agulhas = Agulhas.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/listar_agulhas.html', {'agulhas': agulhas, 'fornecedor': fornecedor})

@login_required
def adicionar_agulha(request, agulha_id):
    agulha = get_object_or_404(Agulhas, pk=agulha_id)

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            previous_quantity = agulha.quantidade
            agulha.quantidade += quantidade
            stock_after_use = agulha.quantidade
            agulha.user = request.user
            agulha.save()

            UpdateAgulhas.objects.create(
                agulha=agulha,
                previous_quantity=previous_quantity,
                new_quantity=agulha.quantidade,
                action='added',
                user=request.user
            )

            AgulhasEntradas.objects.create(
                agulha=agulha,
                previous_quantity=previous_quantity,
                stock_after_use=stock_after_use,
                quantity_added=quantidade,
                user=request.user
            )

            return redirect('listar_agulhas')

        except ValueError:
            context = {'agulha': agulha, 'error': "Por favor, insira um número válido maior que zero."}
            return render(request, 'management/adicionar_agulha.html', context)

    return render(request, 'management/adicionar_agulha.html', {'agulha': agulha})

@login_required
def remover_agulha(request, agulha_id):
    agulha = get_object_or_404(Agulhas, pk=agulha_id)
    context = {'agulha': agulha}

    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('num_field'))
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")

            # Atualiza a quantidade
            previous_quantity = agulha.quantidade
            agulha.quantidade -= quantidade
            stock_after_use = agulha.quantidade
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
                previous_quantity=previous_quantity,
                quantity_removed=quantidade,
                stock_after_use=stock_after_use,
                user=request.user
            )

            context['success'] = True

            return redirect('listar_agulhas')

        except ValueError:
            context['error'] = "Por favor, insira um número válido maior que zero."

    return render(request, 'management/remover_agulha.html', context)

@login_required
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
            previous_stock=F("previous_quantity"),
            stock_after_movement=F("stock_after_use"),
            current_stock=F("agulha__quantidade"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "agulha_tipo", "agulha_tamanho", "previous_stock", "stock_after_movement", "current_stock", "username")
    )

    sai_norm = (sai
        .annotate(
            date=F("date_removed"),
            quantity=F("quantity_removed"),
            direction=Value("saida", output_field=CharField()),
            agulha_tipo=F("agulha__tipo"),
            agulha_tamanho=F("agulha__tamanho"),
            previous_stock=F("previous_quantity"),
            stock_after_movement=F("stock_after_use"),
            current_stock=F("agulha__quantidade"),
            username=F("user__username"),
        )
        .values("date", "quantity", "direction", "agulha_tipo", "agulha_tamanho", "previous_stock", "stock_after_movement", "current_stock", "username")
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


    # 🔹 Existências atuais por (tipo, tamanho)
    existencias = (
        Agulhas.objects
        .values("tipo", "tamanho")
        .annotate(total_exist=Sum("quantidade"))
    )
    # cria um dicionário para lookup rápido
    exist_map = {(row["tipo"], row["tamanho"]): row["total_exist"] or 0 for row in existencias}

    # 🔹 Totais listados
    if tipo == "entradas":
        total_listado = total_entradas
    elif tipo == "saidas":
        total_listado = total_saidas
    else:
        total_listado = None

    # 🔹 Resumo por (tipo, tamanho)
    entradas_por_ag = (
        ent.values("agulha__tipo", "agulha__tamanho")
        .annotate(total_ent=Sum("quantity_added"))
    )
    saidas_por_ag = (
        sai.values("agulha__tipo", "agulha__tamanho")
        .annotate(total_sai=Sum("quantity_removed"))
    )

    resumo_map = {}

    for row in entradas_por_ag:
        k = (row["agulha__tipo"], row["agulha__tamanho"])
        resumo_map[k] = {
            "tipo": k[0],
            "tamanho": k[1],
            "entradas": row["total_ent"] or 0,
            "saidas": 0,
            "existencias": exist_map.get(k, 0),
        }

    for row in saidas_por_ag:
        k = (row["agulha__tipo"], row["agulha__tamanho"])
        if k not in resumo_map:
            resumo_map[k] = {
                "tipo": k[0],
                "tamanho": k[1],
                "entradas": 0,
                "saidas": row["total_sai"] or 0,
                "existencias": exist_map.get(k, 0),
            }
        else:
            resumo_map[k]["saidas"] = row["total_sai"] or 0

    # 🔹 Calcular saldo real
    resumo_por_agulha = []
    for v in resumo_map.values():
        v["saldo"] = (v["existencias"] or 0) + (v["entradas"] or 0) - (v["saidas"] or 0)
        resumo_por_agulha.append(v)

    # 🔹 Ordenar por tipo e tamanho
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

@login_required
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
                categoria=category,
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

@login_required
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

@login_required
def editar_stock(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)

    if request.method == 'POST':
        product = request.POST.get('product')
        min_stock = request.POST.get('min_stock')
        quantity = request.POST.get('quantity')
        fornecedor_id = request.POST.get('fornecedor')
        category_id = request.POST.get('category')

        try:
            fornecedor = Fornecedor.objects.get(id=fornecedor_id)
            category = CategoriaProduto.objects.get(id=category_id)

            stock.product = product
            stock.min_stock = int(min_stock)
            stock.quantity = int(quantity)
            stock.fornecedor = fornecedor
            stock.categoria = category
            stock.user = request.user
            stock.save()

            messages.success(request, "Stock atualizado com sucesso.")
            return redirect('listar_stock')

        except Fornecedor.DoesNotExist:
            messages.error(request, "Fornecedor inválido.")
        except CategoriaProduto.DoesNotExist:
            messages.error(request, "Categoria inválida.")
        except ValueError:
            messages.error(request, "Dados inválidos ao atualizar stock.")

    category = CategoriaProduto.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/editar_stock.html', {
        'stock': stock,
        'fornecedor': fornecedor,
        'category': category
    })

@login_required
def delete_stock(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)

    if request.method == 'POST':
        stock.delete()
        messages.success(request, "Stock removido com sucesso.")
        return redirect('listar_stock')

    return render(request, 'management/delete_stock.html', {'stock': stock})

@login_required
def criar_fornecedor(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        ref_fornecedor = request.POST.get('ref_fornecedor', '').strip()
        email = request.POST.get('email', '').strip()
        telefone = request.POST.get('telefone', '').strip()

        if not nome:
            messages.error(request, "O campo 'Nome' é obrigatório.")
            return render(request, 'management/criar_fornecedor.html', {'form': request.POST})

        Fornecedor.objects.create(
            nome=nome,
            ref_fornecedor=ref_fornecedor,
            email=email,
            telefone=telefone
        )
        messages.success(request, "Fornecedor criado com sucesso!")
        return redirect('main_menu')

    return render(request, 'management/criar_fornecedor.html')


def listar_fornecedores(request):
    fornecedores = Fornecedor.objects.all().order_by('nome')
    return render(request, 'management/listar_fornecedores.html', {'fornecedores': fornecedores})

def editar_fornecedor(request, fornecedor_id):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id)

    if request.method == 'POST':
        nome = request.POST.get('nome')
        ref_fornecedor = request.POST.get('ref_fornecedor', '').strip()
        email = request.POST.get('email', '').strip()
        telefone = request.POST.get('telefone', '').strip()

        if not nome:
            messages.error(request, "O campo 'Nome' é obrigatório.")
            return render(request, 'management/editar_fornecedor.html', {'fornecedor': fornecedor})

        fornecedor.nome = nome
        fornecedor.ref_fornecedor = ref_fornecedor
        fornecedor.email = email
        fornecedor.telefone = telefone
        fornecedor.save()

        messages.success(request, "Fornecedor atualizado com sucesso!")
        return redirect('listar_fornecedores')

    return render(request, 'management/editar_fornecedor.html', {'fornecedor': fornecedor})

def deletar_fornecedor(request, fornecedor_id):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id)

    if request.method == 'POST':
        fornecedor.delete()
        messages.success(request, "Fornecedor removido com sucesso!")
        return redirect('listar_fornecedores')

    return render(request, 'management/deletar_fornecedor.html', {'fornecedor': fornecedor})


def listar_e_adicionar_maquinas(request):
    maquinas = stockMaquinas.objects.all()

    if request.method == 'POST':
        # Criar nova
        fornecedor_id = request.POST.get('fornecedor')
        fornecedor = Fornecedor.objects.get(id=fornecedor_id) if fornecedor_id else None
        stockMaquinas.objects.create(
            machine_number=request.POST.get('machine_number'),
            production_equipment=request.POST.get('production_equipment'),
            model=request.POST.get('model'),
            purpose=request.POST.get('purpose'),
            defined_location=request.POST.get('defined_location'),
            serial_number=request.POST.get('serial_number'),
            manual=request.POST.get('manual'),
            certificado_ce=request.POST.get('certificado_ce'),
            fornecedor=fornecedor,
            contact=request.POST.get('contact'),
            manutenance_date=request.POST.get('manutenance_date') or None,
            user=request.user
        )
        messages.success(request, "Máquina adicionada com sucesso!")

        try:
            fornecedor = Fornecedor.objects.get(id=fornecedor_id) if fornecedor_id else None

            machine_number = request.POST.get('machine_number')
            production_equipment = request.POST.get('production_equipment')
            model = request.POST.get('model')
            purpose = request.POST.get('purpose')
            defined_location = request.POST.get('defined_location')
            serial_number = request.POST.get('serial_number')
            manual = request.POST.get('manual')
            certificado_ce = request.POST.get('certificado_ce')
            contact = request.POST.get('contact')
            manutenance_date = request.POST.get('manutenance_date') or None

            stockMaquinas.objects.create(
                machine_number=machine_number,
                production_equipment=production_equipment,
                model=model,
                purpose=purpose,
                defined_location=defined_location,
                serial_number=serial_number,
                manual=manual,
                certificado_ce=certificado_ce,
                fornecedor=fornecedor,
                contact=contact,
                manutenance_date=manutenance_date,
                user=request.user
            )
            messages.success(request, "Máquina adicionada com sucesso!")
        except Fornecedor.DoesNotExist:
            messages.error(request, "Fornecedor inválido.")
        except ValueError:
            messages.error(request, "Erro ao adicionar máquina. Verifique os dados fornecidos.")

        return redirect('listar_adicionar_maquinas')

    return render(request, 'management/listar_adicionar_maquina.html', {'maquinas': maquinas, 'fornecedores': Fornecedor.objects.all()})


def deletar_maquina(request, maquina_id):
    maquina = get_object_or_404(stockMaquinas, pk=maquina_id)

    if request.method == 'POST':
        maquina.delete()
        messages.success(request, "Máquina removida com sucesso!")
        return redirect('listar_adicionar_maquinas')

    return render(request, 'management/deletar_maquina.html', {'maquina': maquina})

def editar_maquina(request, maquina_id):
    maquina = get_object_or_404(stockMaquinas, pk=maquina_id)

    if request.method == 'POST':
        fornecedor_id = request.POST.get('fornecedor')
        fornecedor = Fornecedor.objects.get(id=fornecedor_id) if fornecedor_id else None

        maquina.machine_number = request.POST.get('machine_number')
        maquina.production_equipment = request.POST.get('production_equipment')
        maquina.model = request.POST.get('model')
        maquina.purpose = request.POST.get('purpose')
        maquina.defined_location = request.POST.get('defined_location')
        maquina.serial_number = request.POST.get('serial_number')
        maquina.manual = request.POST.get('manual')
        maquina.certificado_ce = request.POST.get('certificado_ce')
        maquina.fornecedor = fornecedor
        maquina.contact = request.POST.get('contact')
        maquina.manutenance_date = request.POST.get('manutenance_date') or None
        maquina.user = request.user
        maquina.save()

        messages.success(request, "Máquina atualizada com sucesso!")
        return redirect('listar_adicionar_maquinas')

    return render(request, 'management/editar_maquina.html', {'maquina': maquina, 'fornecedores': Fornecedor.objects.all()})
    
