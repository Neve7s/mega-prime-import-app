from decimal import Decimal

from django.test import TestCase

from .models import HSCode, TaxRule
from .services import estimate


class EstimateTest(TestCase):
    def test_caso_manual(self):
        # FOB 10.000 + flete 1.500 + seguro 100 = CIF 11.600
        # ad-valorem 10% = 1.160 | fodinfa 0.5% = 58 | base IVA 12.818 | IVA 15% = 1.922,70
        r = estimate(Decimal("10000"), Decimal("1500"), Decimal("100"), Decimal("10"))
        self.assertEqual(r["cif"], Decimal("11600.00"))
        self.assertEqual(r["ad_valorem"], Decimal("1160.00"))
        self.assertEqual(r["fodinfa"], Decimal("58.00"))
        self.assertEqual(r["iva"], Decimal("1922.70"))
        self.assertEqual(r["total"], Decimal("14740.70"))

    def test_regla_activa(self):
        TaxRule.objects.create(nombre="Régimen general 2026")
        rule = TaxRule.get_active()
        self.assertIsNotNone(rule)
        self.assertEqual(rule.iva_pct, Decimal("15.00"))
        self.assertTrue(HSCode.objects.create(codigo="6907.21", descripcion="Placas cerámicas", ad_valorem_pct=Decimal("15")))
