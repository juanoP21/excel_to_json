# pdfconvert/serializers/bancolombia.py

from rest_framework import serializers

class MovimientoSerializer(serializers.Serializer):
    fecha          = serializers.DateField(input_formats=['%Y-%m-%d'])
    descripcion    = serializers.CharField()
    sucursal_canal = serializers.CharField(required=False, allow_blank=True)
    referencia1    = serializers.CharField(required=False, allow_blank=True)
    referencia2    = serializers.CharField(required=False, allow_blank=True)
    documento      = serializers.CharField(required=False, allow_blank=True)
    valor          = serializers.DecimalField(max_digits=18, decimal_places=2)

class BancolombiaSerializer(serializers.Serializer):
    empresa               = serializers.CharField()
    numero_cuenta         = serializers.CharField()
    fecha_hora_actual     = serializers.DateTimeField(input_formats=['%d-%m-%Y %H:%M:%S'])
    nit                   = serializers.CharField()
    tipo_cuenta           = serializers.CharField()
    fecha_hora_consulta   = serializers.DateTimeField(input_formats=['%d-%m-%Y %H:%M:%S'])
    impreso_por           = serializers.CharField()
    saldo_efectivo_actual = serializers.DecimalField(max_digits=18, decimal_places=2)
    saldo_canje_actual    = serializers.DecimalField(max_digits=18, decimal_places=2)
    saldo_total_actual    = serializers.DecimalField(max_digits=18, decimal_places=2)
    movimientos           = MovimientoSerializer(many=True)
