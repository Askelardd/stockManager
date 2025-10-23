from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


# ---------- Fornecedor ------------ #

class Fornecedor(models.Model):
    nome = models.CharField(max_length=200)
    ref_fornecedor = models.CharField(max_length=14, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.nome


# ---------- Po ------------ #

class Po(models.Model):
    reference_choices = [
        ('0-0,25', '0-0,25'),
        ('0-0,50', '0-0,50'),
        ('0-1', '0-1'),
        ('0-2', '0-2'),
        ('2-4', '2-4'),
        ('4-8', '4-8'),
        ('6-12', '6-12'),
        ('10-20', '10-20'),
        ('20-40', '20-40'),
        ('40-60', '40-60'),
        ('60-80', '60-80'),
        ('2-6', '2-6'),
        ('5-10', '5-10'),
        ('0-0,20', '0-0,20'),
    ]
    product = models.CharField(max_length=40, default='Pó de Diamante')
    reference = models.CharField(max_length=10, choices=reference_choices)
    min_stock = models.IntegerField()
    quantity = models.IntegerField()
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return f"{self.product} {self.reference}"
    

class updatePo(models.Model):
    ACTION_CHOICES = [
        ('added', 'Added'),
        ('removed', 'Removed'),
    ]

    po = models.ForeignKey(Po, on_delete=models.CASCADE)
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    new_quantity = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    date_updated = models.DateTimeField(auto_now=True)  # <- você só precisa deste

    def __str__(self):
        return f"{self.po} {self.get_action_display()} {self.date_updated}"

class poSaidas(models.Model):
    po = models.ForeignKey(Po, on_delete=models.CASCADE)
    quantity_used = models.PositiveIntegerField()
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    stock_after_use = models.IntegerField(null=True, blank=True, default=0)
    date_used = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} usou {self.quantity_used} de {self.po} em {self.date_used}"

class poEntradas(models.Model):
    po = models.ForeignKey(Po, on_delete=models.CASCADE)
    quantity_added = models.PositiveIntegerField()
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    stock_after_addition = models.IntegerField(null=True, blank=True, default=0)
    date_added = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} adicionou {self.quantity_added} de {self.po} em {self.date_added}"
    
# ---------- Fio ------------ #


class Fios(models.Model):
    material = [
        ('cobre', 'Cobre'),
        ('aco', 'Aço'),
    ]

    size = models.DecimalField(max_digits=10, decimal_places=4)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    weight_unit = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    material = models.CharField(max_length=20, choices=material, default='cobre')
    min_stock = models.IntegerField(null=True, blank=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return f"Fios {self.size}mm - Material {self.material}"
    
class FioUsado(models.Model):
    fio = models.ForeignKey(Fios, on_delete=models.CASCADE)
    size = models.DecimalField(max_digits=10, decimal_places=4)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    material = models.CharField(max_length=20)
    quantidade_usada = models.PositiveIntegerField()
    stock_after_use = models.IntegerField(null=True, blank=True, default=0)
    data_uso = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} usou {self.quantidade_usada} de {self.fio} em {self.data_uso}"
    


class updateFios(models.Model):
    ACTION_CHOICES = [
        ('added', 'Added'),
        ('removed', 'Removed'),
    ]

    fio = models.ForeignKey(Fios, on_delete=models.CASCADE)
    previous_quantity = models.IntegerField()
    stock_after_use = models.IntegerField(null=True, blank=True, default=0)
    new_quantity = models.IntegerField()
    date_updated = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} updated Fio {self.fio.size}mm from {self.previous_quantity} to {self.new_quantity}"
    

class fioSaidas(models.Model):
    fio = models.ForeignKey(Fios, on_delete=models.CASCADE)
    quantity_used = models.PositiveIntegerField()
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    date_used = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} usou {self.quantity_used} de {self.fio} em {self.date_used}"

class fioEntradas(models.Model):
    fio = models.ForeignKey(Fios, on_delete=models.CASCADE)
    quantity_added = models.PositiveIntegerField()
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    date_added = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} adicionou {self.quantity_added} de {self.fio} em {self.date_added}"
    
class FioTransformacao(models.Model):
    origem = models.ForeignKey('Fios', on_delete=models.PROTECT, related_name='transformacoes_origem')
    total_transferido = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    peso_origem_antes = models.DecimalField(max_digits=12, decimal_places=2)
    peso_origem_depois = models.DecimalField(max_digits=12, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Transformação #{self.pk} - {self.origem.size}mm por {self.user or 'Sistema'}"

class FioTransformacaoItem(models.Model):
    transformacao = models.ForeignKey(FioTransformacao, on_delete=models.CASCADE, related_name='itens')
    destino = models.ForeignKey('Fios', on_delete=models.PROTECT, related_name='transformacoes_destino')
    peso_adicionado = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.peso_adicionado}g → {self.destino.size}mm (T#{self.transformacao_id})"
    

# ---------- Stock ------------ #
class CategoriaProduto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

class Stock(models.Model):

    product = models.CharField(max_length=40)
    quantity = models.IntegerField()
    min_stock = models.IntegerField()
    categoria = models.ForeignKey(CategoriaProduto, on_delete=models.CASCADE, null=True, blank=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.product}"
    
class StockEntradas(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity_added = models.PositiveIntegerField()
    date_added = models.DateTimeField(default=timezone.now)
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    stock_after_added = models.IntegerField(null=True, blank=True, default=0)
    descricao = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} adicionou {self.quantity_added} de {self.stock} em {self.date_added}"
    
class StockSaidas(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity_removed = models.PositiveIntegerField()
    date_removed = models.DateTimeField(default=timezone.now)
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    stock_after_use = models.IntegerField(null=True, blank=True, default=0)
    descricao = models.CharField(max_length=100, blank=True, null=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} removeu {self.quantity_removed} de {self.stock} em {self.date_removed}"
    
class UpdateStock(models.Model):
    ACTION_CHOICES = [
        ('added', 'Added'),
        ('removed', 'Removed'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    new_quantity = models.IntegerField()
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    stock_after_use = models.IntegerField(null=True, blank=True, default=0)
    date_updated = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} updated Stock {self.stock.product} from {self.previous_quantity} to {self.new_quantity}"
    

# ---------- Agulhas ------------ #

class Agulhas(models.Model):
    tipo = models.CharField(max_length=100)
    tamanho = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField()
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Agulha {self.tipo} - {self.tamanho}mm"

class UpdateAgulhas(models.Model):
    ACTION_CHOICES = [
        ('added', 'Added'),
        ('removed', 'Removed'),
    ]

    agulha = models.ForeignKey(Agulhas, on_delete=models.CASCADE)
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    date_updated = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} updated Agulha {self.agulha.tamanho}mm from {self.previous_quantity} to {self.new_quantity}"
    
class AgulhasEntradas(models.Model):
    agulha = models.ForeignKey(Agulhas, on_delete=models.CASCADE)
    quantity_added = models.PositiveIntegerField()
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    stock_after_use = models.IntegerField(null=True, blank=True, default=0)
    date_added = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} adicionou {self.quantity_added} de {self.agulha} em {self.date_added}"
    
class AgulhasSaidas(models.Model):
    agulha = models.ForeignKey(Agulhas, on_delete=models.CASCADE)
    quantity_removed = models.PositiveIntegerField()
    previous_quantity = models.IntegerField(null=True, blank=True, default=0)
    stock_after_use = models.IntegerField(null=True, blank=True, default=0)
    date_removed = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} removeu {self.quantity_removed} de {self.agulha} em {self.date_removed}"
    
class stockMaquinas(models.Model):

    option_type = [
        ('Yes', 'Yes'),
        ('No', 'No'),
        ('N/A', 'N/A'),
    ]

    machine_number = models.IntegerField(unique=True)
    production_equipment = models.CharField(max_length=200)
    model = models.CharField(max_length=200, blank=True, null=True)
    purpose = models.CharField(max_length=200, blank=True, null=True)
    defined_location = models.CharField(max_length=200, blank=True, null=True)
    serial_number = models.CharField(max_length=200, blank=True, null=True)
    manual = models.CharField(max_length=10, choices=option_type, blank=True, null=True)
    certificado_ce = models.CharField(max_length=10, choices=option_type, blank=True, null=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, null=True, blank=True)
    contact = models.CharField(max_length=200, blank=True, null=True)
    manutenance_date = models.DateField(blank=True, null=True)
    edited_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Máquina {self.machine_number} - {self.model} - manutenção {self.manutenance_date}"
