from django import forms

from .models import Complaint


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = [
            "tipo", "nombres", "apellidos", "tipo_identificacion", "identificacion",
            "empresa", "correo", "telefono", "direccion", "provincia",
            "producto_servicio", "numero_pedido", "fecha_incidente",
            "monto_reclamado", "detalle", "solicitud", "canal_respuesta",
            "acepta_privacidad",
        ]
        labels = {
            "tipo": "Tipo de solicitud",
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "tipo_identificacion": "Tipo de identificación",
            "identificacion": "Número de identificación",
            "empresa": "Empresa (opcional)",
            "correo": "Correo electrónico",
            "telefono": "Teléfono / WhatsApp",
            "direccion": "Dirección de contacto",
            "provincia": "Provincia",
            "producto_servicio": "Producto o servicio relacionado",
            "numero_pedido": "Número de pedido o factura (opcional)",
            "fecha_incidente": "Fecha del incidente (opcional)",
            "monto_reclamado": "Monto relacionado (USD, opcional)",
            "detalle": "Cuéntanos qué ocurrió",
            "solicitud": "¿Qué solución solicitas?",
            "canal_respuesta": "Canal preferido para recibir respuesta",
            "acepta_privacidad": "He leído el aviso de privacidad y autorizo el uso de mis datos para atender esta solicitud.",
        }
        widgets = {
            "tipo": forms.Select(attrs={"class": "legal-control"}),
            "tipo_identificacion": forms.Select(attrs={"class": "legal-control"}),
            "canal_respuesta": forms.Select(attrs={"class": "legal-control"}),
            "fecha_incidente": forms.DateInput(attrs={
                "type": "date", "class": "legal-control",
            }),
            "monto_reclamado": forms.NumberInput(attrs={
                "min": "0", "step": "0.01", "placeholder": "0.00",
                "class": "legal-control",
            }),
            "detalle": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Describe los hechos, fechas y cualquier información que nos ayude a revisar el caso.",
                "class": "legal-control",
            }),
            "solicitud": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Indica cómo te gustaría que podamos atender tu solicitud.",
                "class": "legal-control",
            }),
            "acepta_privacidad": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 accent-[#0A0A0B]",
            }),
        }

    def clean_identificacion(self):
        return self.cleaned_data["identificacion"].strip()

    def clean_acepta_privacidad(self):
        acepta = self.cleaned_data.get("acepta_privacidad")
        if not acepta:
            raise forms.ValidationError(
                "Debes aceptar el aviso de privacidad para enviar esta solicitud."
            )
        return acepta
