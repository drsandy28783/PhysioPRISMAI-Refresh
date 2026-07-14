"""
Tests for the shared patient_access_allowed() ownership/team-sharing check.

This is a pure function (dict in, bool out) with no Cosmos/Flask dependency,
so these are plain unit tests -- no mocking needed.
"""

import pytest
from patient_access import patient_access_allowed


def _patient(**overrides):
    base = {'physio_id': 'owner@example.com', 'institute': 'Clinic A'}
    base.update(overrides)
    return base


def _actor(**overrides):
    base = {'email': 'other@example.com', 'is_admin': 0, 'is_super_admin': 0, 'institute': ''}
    base.update(overrides)
    return base


@pytest.mark.unit
def test_owner_always_has_access():
    patient = _patient()
    actor = _actor(email='owner@example.com', institute='')
    assert patient_access_allowed(patient, actor) is True


@pytest.mark.unit
def test_owner_has_access_regardless_of_institute_or_admin_fields():
    patient = _patient(institute='Clinic A')
    actor = _actor(email='owner@example.com', institute='Clinic B', is_admin=0, is_super_admin=0)
    assert patient_access_allowed(patient, actor) is True


@pytest.mark.unit
def test_same_institute_non_admin_teammate_has_access():
    """The core new behavior: full team parity, not just admins."""
    patient = _patient(institute='Clinic A')
    actor = _actor(email='teammate@example.com', institute='Clinic A', is_admin=0)
    assert patient_access_allowed(patient, actor) is True


@pytest.mark.unit
def test_same_institute_admin_has_access():
    """Regression guard: today's already-working admin case."""
    patient = _patient(institute='Clinic A')
    actor = _actor(email='admin@example.com', institute='Clinic A', is_admin=1)
    assert patient_access_allowed(patient, actor) is True


@pytest.mark.unit
def test_different_institute_denied_even_for_admin():
    """Regression guard: closes the cross-institute admin-bypass bug."""
    patient = _patient(institute='Clinic A')
    actor = _actor(email='admin@example.com', institute='Clinic B', is_admin=1)
    assert patient_access_allowed(patient, actor) is False


@pytest.mark.unit
def test_different_institute_denied_for_regular_teammate():
    patient = _patient(institute='Clinic A')
    actor = _actor(email='other@example.com', institute='Clinic B', is_admin=0)
    assert patient_access_allowed(patient, actor) is False


@pytest.mark.unit
def test_solo_physios_stay_siloed():
    """Highest-value guard: blank institute must never match blank institute."""
    patient = _patient(physio_id='solo1@example.com', institute='')
    actor = _actor(email='solo2@example.com', institute='')
    assert patient_access_allowed(patient, actor) is False


@pytest.mark.unit
def test_patient_missing_institute_key_entirely():
    patient = {'physio_id': 'solo1@example.com'}  # no 'institute' key at all
    actor = _actor(email='someone@example.com', institute='Clinic A')
    assert patient_access_allowed(patient, actor) is False


@pytest.mark.unit
def test_super_admin_has_global_access():
    patient = _patient(institute='Clinic A')
    actor = _actor(email='sandeep@example.com', institute='', is_super_admin=1)
    assert patient_access_allowed(patient, actor) is True


@pytest.mark.unit
def test_super_admin_access_independent_of_institute_match():
    patient = _patient(institute='Clinic A')
    actor = _actor(email='roopa@example.com', institute='Clinic Z', is_super_admin=1)
    assert patient_access_allowed(patient, actor) is True


@pytest.mark.unit
def test_missing_patient_or_actor_denied():
    assert patient_access_allowed({}, _actor()) is False
    assert patient_access_allowed(_patient(), {}) is False
    assert patient_access_allowed(None, _actor()) is False
    assert patient_access_allowed(_patient(), None) is False
