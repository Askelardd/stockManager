from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Fornecedor(models.Model):
    nome = models.CharField(max_length=40)
    ref_fornecedor = models.CharField(max_length=14)
    email = models.EmailField()
    telefone = models.CharField(max_length=15)

    def __str__(self):
        return self.nome

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
    
#fios cobre e aço

class Fios(models.Model):
    material = [
        ('cobre', 'Cobre'),
        ('aco', 'Aço'),
    ]

    size = models.DecimalField(max_digits=10, decimal_places=4)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    material = models.CharField(max_length=20, choices=material, default='cobre')
    min_stock = models.IntegerField()
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return f"Fios {self.size}mm x {self.weight}g - {self.quantity} unid."

class updateFios(models.Model):
    ACTION_CHOICES = [
        ('added', 'Added'),
        ('removed', 'Removed'),
    ]

    fio = models.ForeignKey(Fios, on_delete=models.CASCADE)
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    date_updated = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} updated Fio {self.fio.size}mm from {self.previous_quantity} to {self.new_quantity}"
    
class updatePo(models.Model):
    ACTION_CHOICES = [
        ('added', 'Added'),
        ('removed', 'Removed'),
    ]

    po = models.ForeignKey(Po, on_delete=models.CASCADE)
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    date_updated = models.DateTimeField(auto_now=True)  # <- você só precisa deste

    def __str__(self):
        return f"{self.po} {self.get_action_display()} {self.date_updated}"

class poSaidas(models.Model):
    po = models.ForeignKey(Po, on_delete=models.CASCADE)
    quantity_used = models.PositiveIntegerField()
    date_used = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} usou {self.quantity_used} de {self.po} em {self.date_used}"

class poEntradas(models.Model):
    po = models.ForeignKey(Po, on_delete=models.CASCADE)
    quantity_added = models.PositiveIntegerField()
    date_added = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} adicionou {self.quantity_added} de {self.po} em {self.date_added}"
    

class fioSaidas(models.Model):
    fio = models.ForeignKey(Fios, on_delete=models.CASCADE)
    quantity_used = models.PositiveIntegerField()
    date_used = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} usou {self.quantity_used} de {self.fio} em {self.date_used}"

class fioEntradas(models.Model):
    fio = models.ForeignKey(Fios, on_delete=models.CASCADE)
    quantity_added = models.PositiveIntegerField()
    date_added = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.username} adicionou {self.quantity_added} de {self.fio} em {self.date_added}"