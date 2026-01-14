"""
Azure OpenAI Client
Replaces Vertex AI (Anthropic Claude) with Azure OpenAI (GPT-4o)
Provides similar API for minimal code changes
"""

import os
import json
from typing import Dict, List, Any, Optional
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion


class AzureOpenAIClient:
    """
    Azure OpenAI client wrapper
    Replaces Vertex AI client with minimal API changes
    """

    def __init__(
        self,
        endpoint: str = None,
        api_key: str = None,
        api_version: str = None,
        deployment_name: str = None
    ):
        """
        Initialize Azure OpenAI client

        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            api_version: API version (default: 2024-12-01-preview)
            deployment_name: Model deployment name (default: gpt-4o)
        """
        self.endpoint = endpoint or os.getenv('AZURE_OPENAI_ENDPOINT')
        self.api_key = api_key or os.getenv('AZURE_OPENAI_API_KEY')
        self.api_version = api_version or os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
        self.deployment_name = deployment_name or os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')

        if not self.endpoint or not self.api_key:
            raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )

        # Configuration
        self.temperature = float(os.getenv('AI_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.getenv('AI_MAX_TOKENS', '2000'))

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        response_format: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Create chat completion (compatible with Vertex AI interface)

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model deployment name (optional, uses default)
            temperature: Sampling temperature (optional, uses default)
            max_tokens: Maximum tokens in response (optional, uses default)
            response_format: Response format dict, e.g., {"type": "json_object"}

        Returns:
            Dict with response data compatible with Vertex AI format
        """
        try:
            # Use defaults if not provided
            model = model or self.deployment_name
            temperature = temperature if temperature is not None else self.temperature
            max_tokens = max_tokens or self.max_tokens

            # Create chat completion
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # Add response format if specified (for JSON mode)
            if response_format:
                kwargs["response_format"] = response_format

            response: ChatCompletion = self.client.chat.completions.create(**kwargs)

            # Extract response data
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Calculate token usage
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

            # Return in Vertex AI compatible format
            return {
                "content": [{"text": content}],  # Anthropic format
                "text": content,  # Direct text access
                "usage": usage,
                "finish_reason": finish_reason,
                "model": model,
                "raw_response": response
            }

        except Exception as e:
            print(f"Azure OpenAI API error: {e}")
            raise

    def generate_clinical_suggestion(
        self,
        system_prompt: str,
        user_prompt: str,
        patient_context: Optional[Dict[str, Any]] = None,
        temperature: float = None,
        return_json: bool = False
    ) -> str:
        """
        Generate clinical suggestion using GPT-4o
        Specialized method for PhysiologicPRISM clinical decision support

        Args:
            system_prompt: System instructions for clinical context
            user_prompt: User's specific question/request
            patient_context: Optional patient data to include
            temperature: Override default temperature
            return_json: Whether to enforce JSON output format

        Returns:
            Generated suggestion text (or JSON string if return_json=True)
        """
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add patient context if provided
        if patient_context:
            context_text = "Patient Context:\n" + json.dumps(patient_context, indent=2)
            messages.append({"role": "system", "content": context_text})

        messages.append({"role": "user", "content": user_prompt})

        # Set response format
        response_format = {"type": "json_object"} if return_json else None

        # Generate response
        response = self.create_chat_completion(
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )

        return response["text"]

    def generate_json_response(
        self,
        system_prompt: str,
        user_prompt: str,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response (enforces JSON output)

        Args:
            system_prompt: System instructions
            user_prompt: User's request
            patient_context: Optional patient context

        Returns:
            Parsed JSON response as dictionary
        """
        response_text = self.generate_clinical_suggestion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            patient_context=patient_context,
            return_json=True
        )

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Response text: {response_text}")
            # Return error structure
            return {"error": "Failed to parse AI response", "raw_response": response_text}


# Clinical System Prompts for PhysiologicPRISM
CLINICAL_SYSTEM_PROMPTS = {
    "base": """You are a clinical decision support AI for physiotherapists.
You provide evidence-based suggestions following:
- ICF (International Classification of Functioning, Disability and Health) framework
- WCPT (World Confederation for Physical Therapy) guidelines
- Evidence-based practice principles

Your responses must be:
1. Clinically accurate and evidence-based
2. Structured and actionable
3. Include contraindications and red flags when relevant
4. Reference clinical reasoning
5. Be professional and concise

Never provide:
- Definitive diagnoses (only suggest provisional diagnoses)
- Treatment without proper assessment context
- Contraindicated interventions without warnings
""",

    "subjective_examination": """You are assisting with subjective examination documentation using the ICF framework.
Suggest relevant questions and areas to explore based on the patient's presenting condition.
Focus on Body Structure, Body Function, Activity Performance, Activity Capacity, and Contextual Factors.
""",

    "objective_assessment": """You are assisting with objective assessment planning.
Suggest appropriate clinical tests and measurements based on the subjective findings.
Consider reliability, validity, and clinical utility of recommended assessments.
Include red flags that would require immediate medical referral.
""",

    "provisional_diagnosis": """You are assisting with clinical reasoning and provisional diagnosis.
Based on subjective and objective findings, suggest likely pathophysiological mechanisms and diagnoses.
Use differential diagnosis approach and highlight key clinical reasoning.
""",

    "patient_perspectives": """You are assisting with patient-centered goal setting.
Suggest patient-reported outcome measures (PROMs) and functional goals based on ICF framework.
Focus on what matters most to the patient in their daily life.
""",

    "initial_plan": """You are assisting with initial treatment planning.
Suggest evidence-based interventions based on assessment findings and provisional diagnosis.
Include precautions, contraindications, and expected outcomes.
""",

    "smart_goals": """You are assisting with SMART goal formulation.
Convert patient goals into Specific, Measurable, Achievable, Relevant, and Time-bound objectives.
Ensure goals are patient-centered and functionally relevant.
""",

    "treatment_plan": """You are assisting with detailed treatment plan development.
Suggest specific interventions, dosage, frequency, and progression criteria.
Base recommendations on current evidence and clinical guidelines.
""",

    "followup": """You are assisting with treatment review and progression.
Suggest modifications to treatment based on patient response and progress.
Consider when to progress, modify, or refer for additional management.
"""
}


def get_system_prompt(prompt_type: str) -> str:
    """
    Get system prompt for specific clinical context

    Args:
        prompt_type: Type of clinical prompt (e.g., 'subjective_examination')

    Returns:
        Combined base + specific system prompt
    """
    base = CLINICAL_SYSTEM_PROMPTS["base"]
    specific = CLINICAL_SYSTEM_PROMPTS.get(prompt_type, "")

    return f"{base}\n\n{specific}".strip()


# Singleton instance
_azure_openai_instance = None


def get_azure_openai_client() -> AzureOpenAIClient:
    """Get or create Azure OpenAI client instance (singleton)"""
    global _azure_openai_instance
    if _azure_openai_instance is None:
        _azure_openai_instance = AzureOpenAIClient()
    return _azure_openai_instance
