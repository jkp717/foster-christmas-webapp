"""Child ID ranges per DHS office: number picking, assignment, and admin editing."""

import pytest

from webapp.models import db, Child, DhsOffice, DhsOfficeIdRange, next_child_id
from tests import factories as f


class TestNextChildId:
    def test_lowest_free_in_office_range(self):
        assert next_child_id({1, 2}, [(1, 100)], [(1, 100), (101, 200)]) == 3

    def test_spills_into_second_range(self):
        used = set(range(1, 101))
        assert next_child_id(used, [(1, 100), (501, 550)], [(1, 100), (501, 550)]) == 501

    def test_full_office_goes_to_overflow_above_highest_range(self):
        used = set(range(1, 101))
        assert next_child_id(used, [(1, 100)], [(1, 100), (101, 500)]) == 501

    def test_office_without_range_goes_to_overflow(self):
        assert next_child_id({501}, [], [(1, 100), (301, 500)]) == 502

    def test_no_ranges_anywhere_starts_at_one(self):
        assert next_child_id(set(), [], []) == 1
        assert next_child_id({1, 2}, [], []) == 3

    def test_split_ids_count_as_used(self):
        from webapp.models import _used_child_numbers
        used = _used_child_numbers(["12A", "12B", "13"])
        assert used == {12, 13}
        assert next_child_id(used, [(12, 20)], [(12, 20)]) == 14


class TestAssignmentOnRegistration:
    def test_ids_follow_office_ranges_and_overflow(self, app):
        with app.app_context():
            lonoke = f.make_office("Lonoke Test", (1, 2))
            f.make_office("Jacksonville Test", (101, 200))
            ids = [f.make_child(dhs_office_id=lonoke.id).child_id for _ in range(3)]
            assert ids == ["1", "2", "201"]

            lonoke.id_ranges.append(DhsOfficeIdRange(range_start=501, range_end=550))
            db.session.commit()
            assert f.make_child(dhs_office_id=lonoke.id).child_id == "501"

    def test_office_without_range_uses_overflow(self, app):
        with app.app_context():
            f.make_office("Jacksonville Test", (101, 200))
            no_range = f.make_office("Not Sure Test")
            assert f.make_child(dhs_office_id=no_range.id).child_id == "201"

    def test_changing_office_keeps_id(self, app):
        with app.app_context():
            lonoke = f.make_office("Lonoke Test", (1, 100))
            jville = f.make_office("Jacksonville Test", (101, 200))
            child = f.make_child(dhs_office_id=lonoke.id)
            assert child.child_id == "1"
            child.dhs_office_id = jville.id
            db.session.commit()
            assert db.session.get(Child, child.id).child_id == "1"

    def test_office_usage_counts(self, app):
        with app.app_context():
            lonoke = f.make_office("Lonoke Test", (1, 100), (501, 550))
            for _ in range(3):
                f.make_child(dhs_office_id=lonoke.id)
            assert lonoke.capacity == 150
            assert lonoke.ids_in_use == 3


class TestOfficeAdmin:
    def _create(self, client, name, *ranges):
        data = {"office": name}
        for i, (start, end) in enumerate(ranges):
            data[f"id_ranges-{i}-range_start"] = str(start)
            data[f"id_ranges-{i}-range_end"] = str(end)
        return client.post("/admin/dhsoffice/new/", data=data, follow_redirects=True)

    def test_create_office_with_range_and_list_shows_usage(self, app, client, login_admin):
        login_admin()
        self._create(client, "Lonoke Test", (1, 100))
        with app.app_context():
            office = db.session.query(DhsOffice).filter_by(office="Lonoke Test").one()
            assert office.range_pairs == [(1, 100)]
        html = client.get("/admin/dhsoffice/").get_data(as_text=True)
        assert "1-100" in html
        assert "0 / 100" in html

    def test_overlapping_range_is_rejected(self, app, client, login_admin):
        login_admin()
        self._create(client, "Lonoke Test", (1, 100))
        resp = self._create(client, "Jacksonville Test", (90, 200))
        assert "overlaps 1-100 (Lonoke Test)" in resp.get_data(as_text=True)
        with app.app_context():
            assert db.session.query(DhsOffice).filter_by(office="Jacksonville Test").first() is None

    def test_overlap_within_same_office_is_rejected(self, app, client, login_admin):
        login_admin()
        resp = self._create(client, "Lonoke Test", (1, 100), (50, 60))
        assert "overlaps" in resp.get_data(as_text=True)
        with app.app_context():
            assert db.session.query(DhsOffice).filter_by(office="Lonoke Test").first() is None

    @pytest.mark.parametrize("start,end", [(0, 10), (50, 10)])
    def test_invalid_range_is_rejected(self, app, client, login_admin, start, end):
        login_admin()
        resp = self._create(client, "Lonoke Test", (start, end))
        assert "is invalid" in resp.get_data(as_text=True)

    def test_child_list_flags_out_of_range_id(self, app, client, login_admin):
        with app.app_context():
            lonoke = f.make_office("Lonoke Test", (1, 1))
            f.make_child(dhs_office_id=lonoke.id)                     # 1, in range
            f.make_child(dhs_office_id=lonoke.id, first_name="Over")  # 2, overflow
        login_admin()
        html = client.get("/admin/child/").get_data(as_text=True)
        assert html.count("outside range") == 1
