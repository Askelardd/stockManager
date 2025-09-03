from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.urls import reverse
from django.utils.timezone import now, make_aware
from django.contrib.auth.models import User
from .models import Po, Fornecedor , updateFios, updatePo, Fios, poSaidas, poEntradas, FioTransformacao, FioTransformacaoItem
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Sum, F
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required


def index(request):
    users = User.objects.all()
    return render(request, 'management/index.html', {'users': users})

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

    usados = updatePo.objects.filter(action='removed')  # base

    # Filtragem por data
    if filtro_data == 'hoje':
        pos = pos.filter(date_added__date=today)
        usados = usados.filter(date_updated__date=today)

    elif filtro_data == 'ontem':
        ontem = today - timedelta(days=1)
        pos = pos.filter(date_added__date=ontem)
        usados = usados.filter(date_updated__date=ontem)

    elif filtro_data == 'semana':
        inicio_semana = today - timedelta(days=today.weekday())
        pos = pos.filter(date_added__date__gte=inicio_semana)
        usados = usados.filter(date_updated__date__gte=inicio_semana)

    elif filtro_data == 'mes':
        pos = pos.filter(date_added__month=today.month, date_added__year=today.year)
        usados = usados.filter(date_updated__month=today.month, date_updated__year=today.year)

    elif filtro_data == 'ano':
        pos = pos.filter(date_added__year=today.year)
        usados = usados.filter(date_updated__year=today.year)

    elif filtro_data == 'entre' and data_inicio and data_fim:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            pos = pos.filter(date_added__date__range=(data_inicio_dt, data_fim_dt))
            usados = usados.filter(date_updated__range=(data_inicio_dt, data_fim_dt))
        except ValueError:
            pass

    # Calcular total usado
    usados = usados.annotate(qtd_usada=F('previous_quantity') - F('new_quantity'))
    quant_usada = usados.aggregate(total=Sum('qtd_usada'))['total'] or 0

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
        'quant_usada': quant_usada,
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