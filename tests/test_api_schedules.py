"""
API tests for schedule endpoints.

Tests schedule generation, retrieval, and deletion for both ASC 842 and IFRS 16.
"""

import pytest
from fastapi import status


@pytest.mark.api
class TestScheduleEndpoints:
    """Test /api/v1/schedules endpoints"""

    def test_generate_asc842_schedule_success(self, client, sample_lease_data):
        """Test successfully generating an ASC 842 schedule"""
        # First create a lease
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]

        # Generate ASC 842 schedule
        response = client.post(f"/api/v1/schedules/asc842/{lease_id}")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["lease_id"] == lease_id
        assert "initial_rou_asset" in data
        assert "initial_lease_liability" in data
        assert "discount_rate" in data

    def test_generate_asc842_schedule_lease_not_found(self, client):
        """Test generating schedule for non-existent lease"""
        response = client.post("/api/v1/schedules/asc842/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_generate_asc842_schedule_duplicate(self, client, sample_lease_data):
        """Test that duplicate schedule generation is prevented"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/asc842/{lease_id}")

        # Try to generate again
        response = client.post(f"/api/v1/schedules/asc842/{lease_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    def test_generate_ifrs16_schedule_success(self, client, sample_lease_data):
        """Test successfully generating an IFRS 16 schedule"""
        # Create a lease
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]

        # Generate IFRS 16 schedule
        response = client.post(f"/api/v1/schedules/ifrs16/{lease_id}")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["lease_id"] == lease_id
        assert "initial_rou_asset" in data
        assert "initial_lease_liability" in data

    def test_get_asc842_schedule_success(self, client, sample_lease_data):
        """Test retrieving an ASC 842 schedule"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/asc842/{lease_id}")

        # Get the schedule
        response = client.get(f"/api/v1/schedules/asc842/{lease_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["lease_id"] == lease_id

    def test_get_asc842_schedule_not_found(self, client, sample_lease_data):
        """Test retrieving non-existent ASC 842 schedule"""
        # Create lease without schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]

        response = client.get(f"/api/v1/schedules/asc842/{lease_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_ifrs16_schedule_success(self, client, sample_lease_data):
        """Test retrieving an IFRS 16 schedule"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/ifrs16/{lease_id}")

        # Get the schedule
        response = client.get(f"/api/v1/schedules/ifrs16/{lease_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["lease_id"] == lease_id

    def test_get_asc842_entries_success(self, client, sample_lease_data):
        """Test retrieving ASC 842 schedule entries"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/asc842/{lease_id}")

        # Get entries
        response = client.get(f"/api/v1/schedules/entries/{lease_id}/asc842")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify entry structure
        assert "period" in data[0]
        assert "lease_payment" in data[0]
        assert "interest_expense" in data[0]

    def test_get_asc842_entries_not_found(self, client, sample_lease_data):
        """Test retrieving entries for lease without schedule"""
        # Create lease without schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]

        response = client.get(f"/api/v1/schedules/entries/{lease_id}/asc842")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_ifrs16_entries_success(self, client, sample_lease_data):
        """Test retrieving IFRS 16 schedule entries"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/ifrs16/{lease_id}")

        # Get entries
        response = client.get(f"/api/v1/schedules/entries/{lease_id}/ifrs16")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_delete_asc842_schedule_success(self, client, sample_lease_data):
        """Test deleting an ASC 842 schedule"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/asc842/{lease_id}")

        # Delete the schedule
        response = client.delete(f"/api/v1/schedules/asc842/{lease_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = client.get(f"/api/v1/schedules/asc842/{lease_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_asc842_schedule_not_found(self, client):
        """Test deleting non-existent ASC 842 schedule"""
        response = client.delete("/api/v1/schedules/asc842/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_ifrs16_schedule_success(self, client, sample_lease_data):
        """Test deleting an IFRS 16 schedule"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/ifrs16/{lease_id}")

        # Delete the schedule
        response = client.delete(f"/api/v1/schedules/ifrs16/{lease_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_both_standards_for_same_lease(self, client, sample_lease_data):
        """Test that both ASC 842 and IFRS 16 schedules can be generated for the same lease"""
        # Create lease
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]

        # Generate both schedules
        asc842_response = client.post(f"/api/v1/schedules/asc842/{lease_id}")
        ifrs16_response = client.post(f"/api/v1/schedules/ifrs16/{lease_id}")

        assert asc842_response.status_code == status.HTTP_201_CREATED
        assert ifrs16_response.status_code == status.HTTP_201_CREATED

        # Verify both exist
        asc842_get = client.get(f"/api/v1/schedules/asc842/{lease_id}")
        ifrs16_get = client.get(f"/api/v1/schedules/ifrs16/{lease_id}")

        assert asc842_get.status_code == status.HTTP_200_OK
        assert ifrs16_get.status_code == status.HTTP_200_OK


@pytest.mark.api
@pytest.mark.integration
class TestScheduleWorkflow:
    """Integration tests for complete schedule workflows"""

    def test_schedule_regeneration_workflow(self, client, sample_lease_data):
        """Test workflow of deleting and regenerating a schedule"""
        # Create lease
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]

        # Generate schedule
        create_response = client.post(f"/api/v1/schedules/asc842/{lease_id}")
        assert create_response.status_code == status.HTTP_201_CREATED
        original_data = create_response.json()

        # Delete schedule
        delete_response = client.delete(f"/api/v1/schedules/asc842/{lease_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Regenerate schedule
        regen_response = client.post(f"/api/v1/schedules/asc842/{lease_id}")
        assert regen_response.status_code == status.HTTP_201_CREATED

        # Verify new schedule has same values (assuming lease wasn't modified)
        new_data = regen_response.json()
        assert new_data["lease_id"] == original_data["lease_id"]

    def test_schedule_after_lease_update(self, client, sample_lease_data):
        """Test that schedule remains valid after lease update"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/asc842/{lease_id}")

        # Update lease
        update_data = {"status": "amended"}
        client.put(f"/api/v1/leases/{lease_id}", json=update_data)

        # Verify schedule still exists
        schedule_response = client.get(f"/api/v1/schedules/asc842/{lease_id}")
        assert schedule_response.status_code == status.HTTP_200_OK

    def test_schedule_entries_ordering(self, client, sample_lease_data):
        """Test that schedule entries are returned in correct order"""
        # Create lease and schedule
        lease_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = lease_response.json()["id"]
        client.post(f"/api/v1/schedules/asc842/{lease_id}")

        # Get entries
        response = client.get(f"/api/v1/schedules/entries/{lease_id}/asc842")
        entries = response.json()

        # Verify ordering by period
        periods = [entry["period"] for entry in entries]
        assert periods == sorted(periods)
        assert periods[0] == 1  # First period should be 1
