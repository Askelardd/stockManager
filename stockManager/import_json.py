import os
import django
import json
from datetime import datetime

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockManager.settings")  # ajuste para seu settings
django.setup()

# Importar modelos
from management.models import stockMaquinas, Fornecedor  # ajuste "myapp" para sua app
from django.contrib.auth.models import User

# Carregar JSON UTF-16
with open("data.json", encoding="utf-16") as f:
    data = json.load(f)

for item in data:
    # Tratar fornecedor
    fornecedor = None
    if item.get("fornecedor"):
        fornecedor, _ = Fornecedor.objects.get_or_create(nome=item["fornecedor"])

    # Tratar datas
    manutenance_date = None
    if item.get("manutenance_date"):
        try:
            manutenance_date = datetime.strptime(item["manutenance_date"], "%d/%m/%Y").date()
        except ValueError:
            pass  # ignora datas inválidas

    # Criar instância stockMaquinas
    machine = stockMaquinas(
        machine_number=item.get("machine_number", ""),
        production_equipment=item.get("production_equipment"),
        model=item.get("model"),
        purpose=item.get("purpose"),
        defined_location=item.get("defined_location"),
        serial_number=item.get("serial_number"),
        manual=item.get("manual"),
        certificado_ce=item.get("certificado_ce"),
        fornecedor=fornecedor,
        contact=item.get("contact"),
        manutenance_date=manutenance_date,
        user=None  # ou algum user default
    )
    machine.save()

print("Importação concluída!")
