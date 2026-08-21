import json
import logging
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from app.ai.client import get_anthropic_client
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Valid diagnoses that Claude is allowed to output
VALID_LLM_DIAGNOSES = {"PRICE_HESITATION", "UX_FRUSTRATION", "UNKNOWN_ABANDONMENT"}

class LLMDiagnosisResponse(BaseModel):
    cause: str = Field(..., description="Must be one of: PRICE_HESITATION, UX_FRUSTRATION, UNKNOWN_ABANDONMENT")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(..., description="Human-readable explanation of why this diagnosis was chosen")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cause": "PRICE_HESITATION",
                "confidence": 0.85,
                "reason": "Customer spent a lot of time on checkout page and repeatedly attempted to apply coupons before leaving."
            }
        }
    )

async def diagnose_checkout_abandonment(telemetry: dict) -> LLMDiagnosisResponse:
    """
    Asks Claude to analyze behavioral telemetry and classify the checkout abandonment.
    Includes validation of the response structure and safe fallback mechanisms.
    """
    # Safe fallback default
    fallback_response = LLMDiagnosisResponse(
        cause="UNKNOWN_ABANDONMENT",
        confidence=0.5,
        reason="Default diagnosis applied due to simulated key or connectivity limitations."
    )

    # Bypass if mock key is configured
    if settings.ANTHROPIC_API_KEY == "mock-key-for-now" or not settings.ANTHROPIC_API_KEY:
        logger.warning("Bypassing live Claude API call: Using mock fallback.")
        return fallback_response

    client = get_anthropic_client()
    
    system_prompt = (
        "You are an expert checkout optimization analyst. Analyze the customer's checkout telemetry data "
        "and determine if their abandonment was due to PRICE_HESITATION (e.g. price shock, coupon errors, high shipping fees) "
        "or UX_FRUSTRATION (e.g. form fields validation errors, page lag, weird inputs). "
        "If you cannot determine the cause, return UNKNOWN_ABANDONMENT.\n\n"
        "You MUST return your answer in JSON matching this schema:\n"
        "{\n"
        '  "cause": "PRICE_HESITATION" | "UX_FRUSTRATION" | "UNKNOWN_ABANDONMENT",\n'
        '  "confidence": float (between 0.0 and 1.0),\n'
        '  "reason": "Detailed string explaining the diagnosis"\n'
        "}\n\n"
        "Do not include any intro, markdown formatting, backticks, or explanation outside the JSON object. Output ONLY the raw JSON."
    )

    user_content = f"Telemetry Data:\n{json.dumps(telemetry, indent=2)}"

    try:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )
        
        raw_text = response.content[0].text.strip()
        
        # Clean any accidental markdown code fences Claude might have included
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        # Parse JSON
        parsed_data = json.loads(raw_text)
        
        # Normalize and validate cause
        cause = parsed_data.get("cause", "").upper()
        if cause not in VALID_LLM_DIAGNOSES:
            parsed_data["cause"] = "UNKNOWN_ABANDONMENT"
            
        validated_res = LLMDiagnosisResponse(**parsed_data)
        logger.info(f"Claude Diagnosis successful: {validated_res.cause} ({validated_res.confidence})")
        return validated_res

    except json.JSONDecodeError as je:
        logger.error(f"Claude returned invalid JSON string: {je}")
        return fallback_response
    except ValidationError as ve:
        logger.error(f"Claude JSON validation failed against schema: {ve}")
        return fallback_response
    except Exception as e:
        logger.error(f"Failed to communicate with Claude API: {e}")
        return fallback_response
