from django.shortcuts import render
from django.contrib.auth.models import User
from .models import Po, Fornecedor , updateFios, updatePo, Fios
from django.shortcuts import render, get_object_or_404, redirect


def index(request):
    users = User.objects.all()
    return render(request, 'management/index.html', {'users': users})

def login(request, user_id):
    if request.method == 'POST':
        # Handle login logic here
        pass
    return render(request, 'management/login.html', {'user_id': user_id})

def listar_pos(request):
    if request.method == 'POST':
        po_id = request.POST.get('po_id')
        if po_id:
            po_item = Po.objects.get(id=po_id)
            if 'increment' in request.POST:
                po_item.quantity += 1
                update_po = updatePo(
                    po=po_item,
                    previous_quantity=po_item.quantity - 1,
                    new_quantity=po_item.quantity,
                    user=request.user,
                    action='increment'
                )
                update_po.save()
            elif 'decrement' in request.POST:
                po_item.quantity -= 1
                update_po = updatePo(
                    po=po_item,
                    previous_quantity=po_item.quantity + 1,
                    new_quantity=po_item.quantity,
                    user=request.user,
                    action='decrement'
                )
                update_po.save()

            po_item.user = request.user
            po_item.save()

        return redirect('listar_pos')

    # GET request
    pos = Po.objects.all()
    fornecedor = Fornecedor.objects.all()
    return render(request, 'management/listar_pos.html', {'pos': pos, 'fornecedor': fornecedor})


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
