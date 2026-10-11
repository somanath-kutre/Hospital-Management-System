from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import DoctorProfile, User
from appointments.models import Appointment
from billing.models import Payment
from billing.views import generate_invoice
from clinical.models import Bed, Encounter, Ward
from patients.models import Patient


class RoleAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", password="x")
        cls.doc = User.objects.create_user("doc", password="x", role="doctor", first_name="A")
        DoctorProfile.objects.create(user=cls.doc, specialization="GM", consultation_fee=500)
        cls.doc2 = User.objects.create_user("doc2", password="x", role="doctor", first_name="B")
        cls.rec = User.objects.create_user("rec", password="x", role="reception")
        cls.pu1 = User.objects.create_user("p1", password="x", role="patient")
        cls.pu2 = User.objects.create_user("p2", password="x", role="patient")
        cls.p1 = Patient.objects.create(user=cls.pu1, first_name="One", date_of_birth="1990-01-01", gender="M")
        cls.p2 = Patient.objects.create(user=cls.pu2, first_name="Two", date_of_birth="1990-01-01", gender="F")
        ward = Ward.objects.create(name="W")
        cls.bed = Bed.objects.create(ward=ward, number="1", daily_charge=1000)

    def login(self, user):
        self.client.force_login(user)

    def test_anonymous_redirected(self):
        r = self.client.get(reverse("patient_list"))
        self.assertEqual(r.status_code, 302)

    def test_patient_cannot_list_patients_or_see_others(self):
        self.login(self.pu1)
        self.assertEqual(self.client.get(reverse("patient_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("patient_detail", args=[self.p2.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("patient_detail", args=[self.p1.pk])).status_code, 200)

    def test_doctor_has_no_billing_and_no_staff_pages(self):
        self.login(self.doc)
        self.assertEqual(self.client.get(reverse("invoice_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("staff_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("patient_list")).status_code, 200)

    def test_reception_cannot_manage_staff_but_can_register_patient(self):
        self.login(self.rec)
        self.assertEqual(self.client.get(reverse("staff_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("patient_add")).status_code, 200)

    def test_admin_pages(self):
        self.login(self.admin)
        for name in ("dashboard", "staff_list", "patient_list", "invoice_list", "encounter_list", "appointment_list"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_dashboards_render_for_every_role(self):
        for u in (self.doc, self.rec, self.pu1):
            self.login(u)
            self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_double_booking_blocked(self):
        day = timezone.localdate() + timedelta(days=1)
        Appointment.objects.create(patient=self.p1, doctor=self.doc, date=day, time="10:00")
        self.login(self.pu2)
        r = self.client.post(
            reverse("appointment_create"),
            {"doctor": self.doc.pk, "date": day.isoformat(), "time": "10:00", "reason": "x"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already has an appointment")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_patient_books_own_appointment(self):
        day = timezone.localdate() + timedelta(days=2)
        self.login(self.pu1)
        r = self.client.post(
            reverse("appointment_create"),
            {"doctor": self.doc.pk, "date": day.isoformat(), "time": "09:00", "reason": "x"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Appointment.objects.get().patient, self.p1)

    def test_doctor_cannot_open_other_doctors_encounter(self):
        enc = Encounter.objects.create(patient=self.p1, doctor=self.doc, visit_type="OPD")
        self.login(self.doc2)
        self.assertEqual(self.client.get(reverse("encounter_detail", args=[enc.pk])).status_code, 404)
        self.login(self.pu2)
        self.assertEqual(self.client.get(reverse("encounter_detail", args=[enc.pk])).status_code, 404)
        self.login(self.pu1)
        self.assertEqual(self.client.get(reverse("encounter_detail", args=[enc.pk])).status_code, 200)

    def test_ipd_bed_lifecycle_and_billing(self):
        self.login(self.rec)
        r = self.client.post(
            reverse("encounter_create"),
            {"patient": self.p1.pk, "doctor": self.doc.pk, "visit_type": "IPD", "bed": self.bed.pk, "chief_complaint": "x"},
        )
        self.assertEqual(r.status_code, 302)
        enc = Encounter.objects.get()
        self.bed.refresh_from_db()
        self.assertTrue(self.bed.is_occupied)

        inv = generate_invoice(enc, self.rec)
        self.assertEqual(inv.total, Decimal("1500"))  # 500 consult + 1 day bed 1000
        Payment.objects.create(invoice=inv, amount=Decimal("500"))
        inv = type(inv).objects.prefetch_related("items", "payments").get(pk=inv.pk)
        self.assertEqual(inv.status, "Partial")
        Payment.objects.create(invoice=inv, amount=Decimal("1000"))
        inv = type(inv).objects.prefetch_related("items", "payments").get(pk=inv.pk)
        self.assertEqual(inv.status, "Paid")

        enc.close("done")
        self.bed.refresh_from_db()
        self.assertFalse(self.bed.is_occupied)

    def test_ipd_requires_bed(self):
        self.login(self.rec)
        r = self.client.post(
            reverse("encounter_create"),
            {"patient": self.p1.pk, "doctor": self.doc.pk, "visit_type": "IPD", "chief_complaint": "x"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Encounter.objects.count(), 0)

    def test_overpayment_rejected(self):
        enc = Encounter.objects.create(patient=self.p1, doctor=self.doc, visit_type="OPD")
        inv = generate_invoice(enc, self.rec)
        self.login(self.rec)
        self.client.post(reverse("invoice_add_payment", args=[inv.pk]), {"amount": "9999", "method": "cash", "paid_on": "2026-01-01"})
        self.assertEqual(Payment.objects.count(), 0)
