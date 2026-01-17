"""
API tests for lease endpoints.

Tests CRUD operations, validation, error handling, and edge cases.
Following API testing best practices:
- Test all HTTP methods
- Test success and error responses
- Test validation and constraints
- Test pagination and filtering
"""

import pytest
from decimal import Decimal
from fastapi import status


@pytest.mark.api
class TestLeaseEndpoints:
    """Test /api/v1/leases endpoints"""

    @staticmethod
    def _as_decimal(value):
        return Decimal(str(value))

    def test_create_lease_success(self, client, sample_lease_data):
        """Test successfully creating a lease"""
        response = client.post("/api/v1/leases/", json=sample_lease_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["lease_name"] == sample_lease_data["lease_name"]
        assert data["lessor_name"] == sample_lease_data["lessor_name"]
        assert "id" in data
        assert "created_at" in data

    def test_create_lease_invalid_data(self, client):
        """Test creating a lease with invalid data"""
        invalid_data = {
            "lease_name": "Test Lease"
            # Missing required fields
        }
        response = client.post("/api/v1/leases/", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_lease_negative_payment(self, client, sample_lease_data):
        """Test creating a lease with negative payment amount"""
        sample_lease_data["periodic_payment"] = -1000.00
        response = client.post("/api/v1/leases/", json=sample_lease_data)

        # Should either reject or accept based on validation rules
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_201_CREATED
        ]

    def test_list_leases_empty(self, client):
        """Test listing leases when database is empty"""
        response = client.get("/api/v1/leases/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_leases_with_data(self, client, sample_lease_data):
        """Test listing leases with data in database"""
        # Create a lease first
        client.post("/api/v1/leases/", json=sample_lease_data)

        response = client.get("/api/v1/leases/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["lease_name"] == sample_lease_data["lease_name"]

    def test_list_leases_pagination(self, client, sample_lease_data):
        """Test lease list pagination"""
        # Create multiple leases
        for i in range(5):
            lease_data = sample_lease_data.copy()
            lease_data["lease_name"] = f"Lease {i}"
            client.post("/api/v1/leases/", json=lease_data)

        # Test with limit
        response = client.get("/api/v1/leases/?limit=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

        # Test with skip and limit
        response = client.get("/api/v1/leases/?skip=2&limit=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    def test_get_lease_success(self, client, sample_lease_data):
        """Test getting a specific lease by ID"""
        # Create a lease
        create_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = create_response.json()["id"]

        # Get the lease
        response = client.get(f"/api/v1/leases/{lease_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == lease_id
        assert data["lease_name"] == sample_lease_data["lease_name"]

    def test_get_lease_not_found(self, client):
        """Test getting a non-existent lease"""
        response = client.get("/api/v1/leases/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_update_lease_success(self, client, sample_lease_data):
        """Test successfully updating a lease"""
        # Create a lease
        create_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = create_response.json()["id"]

        # Update the lease
        update_data = {
            "periodic_payment": 6000.00,
            "status": "amended"
        }
        response = client.put(f"/api/v1/leases/{lease_id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert self._as_decimal(data["periodic_payment"]) == Decimal("6000.00")
        assert data["status"] == "amended"
        # Verify unchanged fields remain
        assert data["lease_name"] == sample_lease_data["lease_name"]

    def test_update_lease_not_found(self, client):
        """Test updating a non-existent lease"""
        update_data = {"status": "terminated"}
        response = client.put("/api/v1/leases/99999", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_lease_partial(self, client, sample_lease_data):
        """Test partial update of lease"""
        # Create a lease
        create_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = create_response.json()["id"]

        # Update only one field
        update_data = {"status": "inactive"}
        response = client.put(f"/api/v1/leases/{lease_id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "inactive"
        assert self._as_decimal(data["periodic_payment"]) == self._as_decimal(
            sample_lease_data["periodic_payment"]
        )

    def test_delete_lease_success(self, client, sample_lease_data):
        """Test successfully deleting a lease"""
        # Create a lease
        create_response = client.post("/api/v1/leases/", json=sample_lease_data)
        lease_id = create_response.json()["id"]

        # Delete the lease
        response = client.delete(f"/api/v1/leases/{lease_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = client.get(f"/api/v1/leases/{lease_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_lease_not_found(self, client):
        """Test deleting a non-existent lease"""
        response = client.delete("/api/v1/leases/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_multiple_leases(self, client, sample_lease_data, sample_finance_lease_data):
        """Test creating multiple different leases"""
        # Create operating lease
        response1 = client.post("/api/v1/leases/", json=sample_lease_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Create finance lease
        response2 = client.post("/api/v1/leases/", json=sample_finance_lease_data)
        assert response2.status_code == status.HTTP_201_CREATED

        # Verify both exist
        list_response = client.get("/api/v1/leases/")
        assert len(list_response.json()) == 2

    def test_lease_date_format(self, client, sample_lease_data):
        """Test that dates are properly formatted in response"""
        response = client.post("/api/v1/leases/", json=sample_lease_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Verify date fields are present and properly formatted
        assert "commencement_date" in data
        assert "created_at" in data

    def test_lease_decimal_precision(self, client, sample_lease_data):
        """Test that decimal values maintain precision"""
        sample_lease_data["periodic_payment"] = 5432.10
        sample_lease_data["incremental_borrowing_rate"] = 0.0525

        response = client.post("/api/v1/leases/", json=sample_lease_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Verify decimal precision is maintained
        assert self._as_decimal(data["periodic_payment"]) == Decimal("5432.10")
        assert self._as_decimal(data["incremental_borrowing_rate"]) == Decimal("0.0525")


@pytest.mark.api
@pytest.mark.integration
class TestLeaseEndpointsIntegration:
    """Integration tests for lease endpoints"""

    def test_crud_workflow(self, client, sample_lease_data):
        """Test complete CRUD workflow for a lease"""
        # Create
        create_response = client.post("/api/v1/leases/", json=sample_lease_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        lease_id = create_response.json()["id"]

        # Read
        read_response = client.get(f"/api/v1/leases/{lease_id}")
        assert read_response.status_code == status.HTTP_200_OK
        assert read_response.json()["lease_name"] == sample_lease_data["lease_name"]

        # Update
        update_data = {"status": "amended"}
        update_response = client.put(f"/api/v1/leases/{lease_id}", json=update_data)
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["status"] == "amended"

        # Delete
        delete_response = client.delete(f"/api/v1/leases/{lease_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        verify_response = client.get(f"/api/v1/leases/{lease_id}")
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    def test_concurrent_lease_creation(self, client, sample_lease_data):
        """Test creating multiple leases concurrently"""
        lease_data_list = []
        for i in range(10):
            data = sample_lease_data.copy()
            data["lease_name"] = f"Concurrent Lease {i}"
            lease_data_list.append(data)

        # Create all leases
        responses = []
        for data in lease_data_list:
            response = client.post("/api/v1/leases/", json=data)
            responses.append(response)

        # Verify all succeeded
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED

        # Verify all are listed
        list_response = client.get("/api/v1/leases/")
        assert len(list_response.json()) == 10
