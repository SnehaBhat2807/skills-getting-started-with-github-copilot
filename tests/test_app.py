"""
Test suite for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_state = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state
    for name, activity in activities.items():
        activity["participants"] = original_state[name]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_get_activities_contains_required_fields(self, client, reset_activities):
        """Test that each activity contains required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_get_activities_participants_are_strings(self, client, reset_activities):
        """Test that participants are strings (emails)"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            for participant in activity_data["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant_success(self, client, reset_activities):
        """Test successful signup of a new participant"""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "alex@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]
        
        # Verify participant was added
        assert "alex@mergington.edu" in activities["Basketball Team"]["participants"]
    
    def test_signup_to_activity_with_existing_participants(self, client, reset_activities):
        """Test signup to an activity that already has participants"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_participant_fails(self, client, reset_activities):
        """Test that signing up an already registered participant fails"""
        # First signup should succeed
        response1 = client.post(
            "/activities/Tennis Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            "/activities/Tennis Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client, reset_activities):
        """Test that signup to non-existent activity fails"""
        response = client.post(
            "/activities/Fake Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_response_message_format(self, client, reset_activities):
        """Test that signup response message contains email and activity name"""
        email = "testuser@mergington.edu"
        activity = "Drama Club"
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        message = response.json()["message"]
        assert email in message
        assert activity in message
    
    def test_signup_with_special_characters_in_activity_name(self, client, reset_activities):
        """Test signup works with activities that have spaces"""
        response = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "java@mergington.edu"}
        )
        assert response.status_code == 200
        assert "java@mergington.edu" in activities["Programming Class"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant_success(self, client, reset_activities):
        """Test successful unregistration of an existing participant"""
        # First add a participant
        client.post(
            "/activities/Art Studio/signup",
            params={"email": "artist@mergington.edu"}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Art Studio/unregister",
            params={"email": "artist@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        assert "artist@mergington.edu" not in activities["Art Studio"]["participants"]
    
    def test_unregister_from_activity_with_existing_participants(self, client, reset_activities):
        """Test unregistering from activity with pre-existing participants"""
        # Chess Club already has michael@mergington.edu
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_participant_fails(self, client, reset_activities):
        """Test that unregistering a non-existent participant fails"""
        response = client.delete(
            "/activities/Science Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_from_nonexistent_activity_fails(self, client, reset_activities):
        """Test that unregistering from non-existent activity fails"""
        response = client.delete(
            "/activities/Fake Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_response_message_format(self, client, reset_activities):
        """Test that unregister response message contains email and activity name"""
        email = "debate@mergington.edu"
        activity = "Debate Team"
        
        # First signup
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        message = response.json()["message"]
        assert email in message
        assert activity in message


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_signup_and_see_in_activities(self, client, reset_activities):
        """Test that newly signed up participant appears in activities list"""
        email = "integration@mergington.edu"
        activity = "Gym Class"
        
        # Signup
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Get activities and verify
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
    
    def test_signup_unregister_workflow(self, client, reset_activities):
        """Test complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity = "Tennis Club"
        
        # Initially not registered
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify participant is added
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        unreg_response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert unreg_response.status_code == 200
        
        # Verify participant is removed
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_participants_signup(self, client, reset_activities):
        """Test signing up multiple participants to same activity"""
        activity = "Science Club"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in emails:
            assert email in participants
