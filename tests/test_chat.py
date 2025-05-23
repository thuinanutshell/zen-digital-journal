"""
Gemini API Test Script
A standalone script to test Gemini API functionality with minimal setup.
"""

import os
import sys
import json
from datetime import datetime
import google.generativeai as genai


def load_environment():
    """Load environment variables - modify as needed for your setup."""
    # Option 1: Load from .env file (uncomment if using python-dotenv)
    # from dotenv import load_dotenv
    # load_dotenv()
    
    # Option 2: Set directly here for testing (not recommended for production)
    # os.environ['GEMINI_API_KEY'] = 'your-api-key-here'
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY environment variable not set")
        print("Please set it using one of these methods:")
        print("1. export GEMINI_API_KEY='your-api-key'")
        print("2. Create a .env file with GEMINI_API_KEY=your-api-key")
        print("3. Uncomment and modify the direct assignment in this script")
        sys.exit(1)
    
    return api_key


def test_basic_api_connection(api_key):
    """Test basic API connection and model initialization."""
    print("🔧 Testing basic API connection...")
    
    try:
        genai.configure(api_key=api_key)
        print("✅ API configured successfully")
        
        # Test model creation
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        print("✅ Model created successfully")
        
        return model
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return None


def test_simple_generation(model):
    """Test simple text generation."""
    print("\n🧪 Testing simple text generation...")
    
    try:
        response = model.generate_content("Hello! Please respond with a short greeting.")
        
        if response and response.text:
            print(f"✅ Simple generation successful:")
            print(f"Response: {response.text.strip()}")
            return True
        else:
            print("❌ No response text received")
            return False
            
    except Exception as e:
        print(f"❌ Simple generation failed: {e}")
        return False


def test_with_system_instruction(api_key):
    """Test with system instruction (similar to your chat app)."""
    print("\n🎭 Testing with system instruction...")
    
    try:
        system_instruction = (
            "You are Kai, a compassionate journaling companion. "
            "Keep responses brief and supportive, under 50 words for this test."
        )
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system_instruction
        )
        
        response = model.generate_content("I'm feeling a bit stressed today.")
        
        if response and response.text:
            print(f"✅ System instruction test successful:")
            print(f"Response: {response.text.strip()}")
            return True
        else:
            print("❌ No response with system instruction")
            return False
            
    except Exception as e:
        print(f"❌ System instruction test failed: {e}")
        return False


def test_conversation_history():
    """Test conversation with history (similar to your chat flow)."""
    print("\n💬 Testing conversation with history...")
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction="You are a helpful assistant. Keep responses brief."
        )
        
        # Simulate conversation history
        conversation_history = [
            {"role": "user", "parts": ["What's 2+2?"]},
            {"role": "model", "parts": ["2+2 equals 4."]},
            {"role": "user", "parts": ["What about 3+3?"]}
        ]
        
        response = model.generate_content(conversation_history)
        
        if response and response.text:
            print(f"✅ Conversation history test successful:")
            print(f"Response: {response.text.strip()}")
            return True
        else:
            print("❌ No response with conversation history")
            return False
            
    except Exception as e:
        print(f"❌ Conversation history test failed: {e}")
        return False


def test_generation_config():
    """Test with generation configuration (similar to your settings)."""
    print("\n⚙️ Testing with generation config...")
    
    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        response = model.generate_content(
            "Tell me a very short joke.",
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 100,
                "top_p": 0.8
            }
        )
        
        if response and response.text:
            print(f"✅ Generation config test successful:")
            print(f"Response: {response.text.strip()}")
            return True
        else:
            print("❌ No response with generation config")
            return False
            
    except Exception as e:
        print(f"❌ Generation config test failed: {e}")
        return False


def test_error_handling():
    """Test error handling scenarios."""
    print("\n🚨 Testing error handling...")
    
    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        # Test with potentially problematic content
        response = model.generate_content("")
        
        if response:
            print("✅ Empty input handled gracefully")
        else:
            print("⚠️ Empty input returned no response")
            
    except Exception as e:
        print(f"✅ Empty input error handled: {e}")
    
    return True


def run_all_tests():
    """Run comprehensive API tests."""
    print("🚀 Starting Gemini API Tests")
    print("=" * 50)
    
    # Load environment
    api_key = load_environment()
    
    test_results = []
    
    # Test 1: Basic connection
    model = test_basic_api_connection(api_key)
    test_results.append(("Basic Connection", model is not None))
    
    if not model:
        print("\n❌ Cannot proceed with other tests - basic connection failed")
        return
    
    # Test 2: Simple generation
    test_results.append(("Simple Generation", test_simple_generation(model)))
    
    # Test 3: System instruction
    test_results.append(("System Instruction", test_with_system_instruction(api_key)))
    
    # Test 4: Conversation history
    test_results.append(("Conversation History", test_conversation_history()))
    
    # Test 5: Generation config
    test_results.append(("Generation Config", test_generation_config()))
    
    # Test 6: Error handling
    test_results.append(("Error Handling", test_error_handling()))
    
    # Results summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Gemini API setup is working correctly.")
    elif passed > 0:
        print("⚠️ Some tests passed. Check the failures above.")
    else:
        print("❌ All tests failed. Check your API key and network connection.")


def interactive_test():
    """Interactive test mode for manual testing."""
    print("\n🔧 Interactive Test Mode")
    print("Type 'quit' to exit")
    
    try:
        api_key = load_environment()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction="You are a helpful assistant."
        )
        
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            try:
                response = model.generate_content(user_input)
                if response and response.text:
                    print(f"AI: {response.text.strip()}")
                else:
                    print("AI: (No response generated)")
            except Exception as e:
                print(f"Error: {e}")
    
    except Exception as e:
        print(f"Interactive test setup failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        run_all_tests()
        
        # Offer interactive mode
        response = input("\n🤔 Would you like to try interactive mode? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            interactive_test()