"""
Test Vision-RAG API endpoint with a property image.
"""
import requests
import json
import sys

def test_vision_rag(image_path, api_url="http://localhost:8000"):
    """Test Vision-RAG endpoint."""
    
    endpoint = f"{api_url}/api/v1/vision-rag/analyze"
    
    # Query params
    params = {
        "property_id": "test-property-001",
        "user_id": "test-user",
        "include_rag_insights": "true"
    }
    
    # Read image file
    try:
        with open(image_path, 'rb') as f:
            files = {'file': ('test-image.jpg', f, 'image/jpeg')}
            
            print(f"🚀 Sending request to: {endpoint}")
            print(f"📸 Image: {image_path}")
            print(f"⏳ Waiting for response...\n")
            
            response = requests.post(
                endpoint,
                params=params,
                files=files,
                timeout=60
            )
            
            print(f"✅ Status Code: {response.status_code}\n")
            
            if response.status_code == 200:
                result = response.json()
                print("=" * 60)
                print("VISION-RAG ANALYSIS RESULT")
                print("=" * 60)
                print(json.dumps(result, indent=2))
                print("=" * 60)
                return result
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else "reference_files/test-image.jpg"
    test_vision_rag(image_path)
