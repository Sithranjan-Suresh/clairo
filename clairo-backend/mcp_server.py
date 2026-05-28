import httpx
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_URL = "https://web-production-ca7ed.up.railway.app"

app = Server("clairo-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="score_claim",
            description="Score a medical insurance claim for denial risk before submission. Returns a 0-100 risk score, risk level (LOW/MEDIUM/HIGH), specific rule flags, and a remediation recommendation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cpt_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of CPT procedure codes being billed"
                    },
                    "payer": {
                        "type": "string",
                        "description": "Insurance payer name (e.g. UHC, Aetna, BCBS, Cigna, Humana)"
                    },
                    "documentation_notes": {
                        "type": "string",
                        "description": "Clinical documentation notes describing what was submitted with the claim"
                    }
                },
                "required": ["cpt_codes", "payer", "documentation_notes"]
            }
        ),
        Tool(
            name="generate_appeal",
            description="Generate a formal, citation-backed insurance appeal letter from a structured claim and denial classification. Returns a complete appeal letter with confidence score.",
            inputSchema={
                "type": "object",
                "properties": {
                    "structured_claim": {
                        "type": "object",
                        "description": "Structured claim data with fields: payer, patient_id, cpt_codes, denial_reason, billed_amount, denied_amount, service_date"
                    },
                    "classification": {
                        "type": "string",
                        "description": "Denial classification: medical_necessity, prior_authorization, coding_mismatch, eligibility, documentation_gap, or timely_filing"
                    }
                },
                "required": ["structured_claim", "classification"]
            }
        ),
        Tool(
            name="retrieve_policy",
            description="Retrieve relevant payer policy sections for a denied procedure. Uses semantic search over real payer policy documents to find the most relevant coverage criteria.",
            inputSchema={
                "type": "object",
                "properties": {
                    "payer": {
                        "type": "string",
                        "description": "Insurance payer name"
                    },
                    "cpt": {
                        "type": "string",
                        "description": "CPT procedure code"
                    },
                    "denial_reason": {
                        "type": "string",
                        "description": "The stated denial reason from the payer"
                    },
                    "classification": {
                        "type": "string",
                        "description": "Denial classification category"
                    }
                },
                "required": ["payer", "cpt", "denial_reason"]
            }
        ),
        Tool(
            name="check_appeal_viability",
            description="Check the viability of an insurance appeal before submitting. Returns High/Medium/Low viability rating and expected recovery probability.",
            inputSchema={
                "type": "object",
                "properties": {
                    "confidence_score": {
                        "type": "integer",
                        "description": "Confidence score from appeal generation (0-100)"
                    },
                    "classification": {
                        "type": "string",
                        "description": "Denial classification category"
                    },
                    "payer": {
                        "type": "string",
                        "description": "Insurance payer name"
                    }
                },
                "required": ["confidence_score", "classification", "payer"]
            }
        ),
        Tool(
            name="get_analytics_summary",
            description="Get practice-level denial analytics including total denials processed, appeal rate, average risk score, denied revenue, and benchmark comparison against industry averages.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="run_full_pipeline",
            description="Run the complete CLAIRO denial-to-appeal pipeline autonomously. Given a structured claim, this tool orchestrates policy retrieval, appeal generation, viability scoring, and returns everything needed for submission.",
            inputSchema={
                "type": "object",
                "properties": {
                    "structured_claim": {
                        "type": "object",
                        "description": "Structured claim data"
                    },
                    "classification": {
                        "type": "string",
                        "description": "Denial classification"
                    }
                },
                "required": ["structured_claim", "classification"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with httpx.AsyncClient(timeout=60.0) as client:

        if name == "score_claim":
            response = await client.post(
                f"{BASE_URL}/risk/score-claim",
                json=arguments
            )
            return [TextContent(type="text", text=response.text)]

        elif name == "generate_appeal":
            response = await client.post(
                f"{BASE_URL}/appeal/generate-from-claim",
                json=arguments
            )
            return [TextContent(type="text", text=response.text)]

        elif name == "retrieve_policy":
            response = await client.get(
                f"{BASE_URL}/rag/retrieve",
                params=arguments
            )
            return [TextContent(type="text", text=response.text)]

        elif name == "check_appeal_viability":
            response = await client.post(
                f"{BASE_URL}/export/viability",
                json=arguments
            )
            return [TextContent(type="text", text=response.text)]

        elif name == "get_analytics_summary":
            response = await client.get(f"{BASE_URL}/analytics/summary")
            return [TextContent(type="text", text=response.text)]

        elif name == "run_full_pipeline":
            structured_claim = arguments["structured_claim"]
            classification = arguments["classification"]
            cpt_codes = structured_claim.get("cpt_codes", [])
            cpt = cpt_codes[0] if cpt_codes else ""
            payer = structured_claim.get("payer", "")
            denial_reason = structured_claim.get("denial_reason", "")

            # Step 1: Retrieve policy
            policy_response = await client.get(
                f"{BASE_URL}/rag/retrieve",
                params={
                    "payer": payer,
                    "cpt": cpt,
                    "denial_reason": denial_reason,
                    "classification": classification
                }
            )

            # Step 2: Generate appeal
            appeal_response = await client.post(
                f"{BASE_URL}/appeal/generate-from-claim",
                json={
                    "structured_claim": structured_claim,
                    "classification": classification
                }
            )
            appeal_data = appeal_response.json()
            confidence_score = appeal_data.get("confidence_score", 70)

            # Step 3: Check viability
            viability_response = await client.post(
                f"{BASE_URL}/export/viability",
                json={
                    "confidence_score": confidence_score,
                    "classification": classification,
                    "payer": payer
                }
            )

            import json
            result = {
                "pipeline": "complete",
                "policy_evidence": policy_response.json(),
                "appeal": appeal_data,
                "viability": viability_response.json()
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())