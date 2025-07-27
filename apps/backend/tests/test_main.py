"""
Tests for the main module.
"""


def test_read_root(client):
    """Test the root endpoint returns the expected response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world"}
