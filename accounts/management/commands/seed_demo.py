from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import DoctorProfile, User
from appointments.models import Appointment
from billing.models import Payment
from billing.views import generate_invoice
from clinical.models import Bed, Encounter, Prescription, PrescriptionItem, Treatment, Ward
from patients.models import Patient


class Command(BaseCommand):
    help = "Create demo users, wards/beds, patients and sample records."

    def handle(self, *args, **options):
        if User.objects.filter(username="admin").exists():
            self.stdout.write("Demo data already present - nothing to do.")
            return

        admin = User.objects.create_superuser("admin", "admin@example.com", "admin123", first_name="System", last_name="Admin")

        def doctor(username, first, last, spec, fee, room):
            u = User.objects.create_user(username, password="doctor123", first_name=first, last_name=last, role="doctor")
            DoctorProfile.objects.create(user=u, specialization=spec, qualification="MBBS, MD", consultation_fee=fee, room=room)
            return u

        d1 = doctor("dr_sharma", "Anil", "Sharma", "General Medicine", 500, "101")
        d2 = doctor("dr_rao", "Meera", "Rao", "Pediatrics", 600, "102")
        User.objects.create_user("reception", password="reception123", first_name="Priya", last_name="Nair", role="reception")

        ward = Ward.objects.create(name="General Ward")
        private = Ward.objects.create(name="Private Ward")
        beds = [Bed.objects.create(ward=ward, number=str(n), daily_charge=1000) for n in range(1, 6)]
        beds += [Bed.objects.create(ward=private, number=f"P{n}", daily_charge=3000) for n in range(1, 4)]

        pu = User.objects.create_user("patient1", password="patient123", first_name="Ravi", last_name="Kumar", role="patient")
        p1 = Patient.objects.create(
            user=pu, first_name="Ravi", last_name="Kumar", date_of_birth=date(1988, 4, 12), gender="M",
            blood_group="B+", phone="9876543210", address="12 MG Road, Bengaluru", allergies="Penicillin",
        )
        p2 = Patient.objects.create(
            first_name="Sunita", last_name="Devi", date_of_birth=date(1975, 9, 3), gender="F",
            blood_group="O+", phone="9123456780", chronic_conditions="Type 2 diabetes",
        )

        today = timezone.localdate()
        Appointment.objects.create(patient=p1, doctor=d1, date=today + timedelta(days=1), time=time(10, 30), reason="Follow-up", created_by=admin)
        Appointment.objects.create(patient=p2, doctor=d2, date=today + timedelta(days=2), time=time(11, 0), reason="Check-up", created_by=admin)

        # Completed OPD visit with prescription, treatment and a part-paid invoice
        opd = Encounter.objects.create(patient=p1, doctor=d1, visit_type="OPD", chief_complaint="Fever and cough for 3 days",
                                       diagnosis="Viral upper respiratory infection", notes="Temp 100.4 F, chest clear")
        Treatment.objects.create(encounter=opd, title="Nebulisation", charge=Decimal("250"), performed_by=d1)
        rx = Prescription.objects.create(encounter=opd, doctor=d1, advice="Rest, warm fluids. Review if fever persists > 3 days.")
        PrescriptionItem.objects.create(prescription=rx, medicine="Paracetamol", dosage="650 mg", frequency="1-1-1", duration="3 days", instructions="after food")
        PrescriptionItem.objects.create(prescription=rx, medicine="Cetirizine", dosage="10 mg", frequency="0-0-1", duration="5 days")
        opd.close("Advised rest and review as needed.")
        inv = generate_invoice(opd, admin)
        Payment.objects.create(invoice=inv, amount=Decimal("500"), method="upi", reference="UPI123", received_by=admin)

        # Active IPD admission
        bed = beds[0]
        Encounter.objects.create(patient=p2, doctor=d1, visit_type="IPD", bed=bed, chief_complaint="Uncontrolled blood sugar, vomiting")
        Bed.objects.filter(pk=bed.pk).update(is_occupied=True)

        self.stdout.write(self.style.SUCCESS(
            "Demo data created.\n"
            "  admin / admin123   dr_sharma / doctor123   dr_rao / doctor123\n"
            "  reception / reception123   patient1 / patient123"
        ))
