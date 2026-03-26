from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


class AIAgentService:
    def __init__(self) -> None:
        self._provider = os.getenv("AI_PROVIDER", "local")
        self._model = os.getenv("LOCAL_LLM_MODEL", "llama3")
        self._base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/api/generate")

    def summarize_and_compare(self, prompt: str, fallback: str) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(self._base_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(req, timeout=2.5) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            text = str(raw.get("response", "")).strip()
            if text:
                return text
        except (URLError, TimeoutError, ValueError, OSError):
            pass
        return fallback

    def assess_eligibility(self, business_profile: dict, grant_structured_data: dict, eligibility_text: str) -> dict:
        fallback = self._fallback_assessment(business_profile, grant_structured_data, eligibility_text)
        prompt = (
            "You are a grant eligibility analyst.\n"
            "Your job:\n"
            "1. Determine if a business qualifies for a grant\n"
            "2. Be strict and conservative\n"
            "3. Do NOT assume missing information\n"
            "4. If unsure, mark as PARTIAL\n"
            "Return ONLY valid JSON with keys: eligibility, confidence, key_reasons, missing_requirements, recommended_action.\n\n"
            f"Business Profile:\n{json.dumps(business_profile)}\n\n"
            f"Grant Details:\n{json.dumps(grant_structured_data)}\n{eligibility_text}\n"
        )
        if self._provider == "cloud":
            # Cloud model integration reserved by design. For now use fallback for deterministic behavior.
            return fallback
        text = self.summarize_and_compare(prompt=prompt, fallback=json.dumps(fallback))
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return {
                    "eligibility": str(parsed.get("eligibility", fallback["eligibility"])),
                    "confidence": int(parsed.get("confidence", fallback["confidence"])),
                    "key_reasons": list(parsed.get("key_reasons", fallback["key_reasons"])),
                    "missing_requirements": list(parsed.get("missing_requirements", fallback["missing_requirements"])),
                    "recommended_action": str(parsed.get("recommended_action", fallback["recommended_action"])),
                }
        except (ValueError, TypeError):
            pass
        return fallback

    def extract_eligibility_criteria(self, cleaned_text: str, fallback: dict) -> dict:
        prompt = (
            "Extract structured eligibility criteria from the content below.\n"
            "Rules:\n"
            "- Do NOT hallucinate\n"
            "- If a field is not stated, return null or []\n"
            "- Be precise and conservative\n"
            "Return ONLY JSON with keys: industries, locations, business_size, must_have, not_allowed.\n\n"
            f"Content:\n\n{cleaned_text[:7000]}"
        )
        if self._provider == "cloud":
            return fallback
        raw = self.summarize_and_compare(prompt=prompt, fallback=json.dumps(fallback))
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return fallback
            return {
                "industries": self._coerce_list(parsed.get("industries"), fallback.get("industries", [])),
                "locations": self._coerce_list(parsed.get("locations"), fallback.get("locations", [])),
                "business_size": str(parsed.get("business_size") or fallback.get("business_size") or ""),
                "must_have": self._coerce_list(parsed.get("must_have"), fallback.get("must_have", [])),
                "not_allowed": self._coerce_list(parsed.get("not_allowed"), fallback.get("not_allowed", [])),
            }
        except (ValueError, TypeError):
            return fallback

    def classify_listing_page(self, cleaned_html: str, fallback: bool) -> bool:
        prompt = (
            "You are a classifier. Determine if the HTML content is a listing page that contains many links to grant items.\n"
            "Return ONLY one of: LISTING or NOT_LISTING.\n\n"
            f"HTML:\n{cleaned_html[:4000]}"
        )
        if self._provider == "cloud":
            return fallback
        raw = self.summarize_and_compare(prompt=prompt, fallback="LISTING" if fallback else "NOT_LISTING")
        answer = str(raw).strip().upper()
        if "LISTING" in answer and "NOT" not in answer:
            return True
        if "NOT_LISTING" in answer or "NOT" in answer:
            return False
        return fallback

    def extract_links_from_html(self, cleaned_html: str) -> list[str]:
        prompt = (
            "From the HTML below, extract URLs that likely lead to individual grant pages.\n"
            "Return only URLs, one per line.\n\n"
            f"HTML:\n{cleaned_html[:4000]}"
        )
        if self._provider == "cloud":
            return []
        raw = self.summarize_and_compare(prompt=prompt, fallback="")
        lines = [line.strip() for line in raw.splitlines()]
        urls = [line for line in lines if line.startswith("http://") or line.startswith("https://")]
        return urls

    def extract_grant_fields(self, cleaned_text: str, fallback: dict) -> dict:
        prompt = (
            "You are an information extraction engine.\n"
            "Extract structured grant information from messy text.\n"
            "Rules:\n"
            "- Do NOT hallucinate\n"
            "- If not found, return null\n"
            "- Be precise\n"
            "Return ONLY JSON with keys: title, provider, amount, deadline, eligibility_summary, industry, location, key_requirements.\n\n"
            f"Extract grant details from the content below:\n\n{cleaned_text[:7000]}"
        )
        if self._provider == "cloud":
            return fallback
        raw = self.summarize_and_compare(prompt=prompt, fallback=json.dumps(fallback))
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return fallback
            return {
                "title": parsed.get("title") or fallback.get("title"),
                "provider": parsed.get("provider") or fallback.get("provider"),
                "amount": parsed.get("amount") or fallback.get("amount"),
                "deadline": parsed.get("deadline") or fallback.get("deadline"),
                "eligibility_summary": parsed.get("eligibility_summary") or fallback.get("eligibility_summary"),
                "industry": parsed.get("industry") if isinstance(parsed.get("industry"), list) else fallback.get("industry", []),
                "location": parsed.get("location") or fallback.get("location"),
                "key_requirements": parsed.get("key_requirements")
                if isinstance(parsed.get("key_requirements"), list)
                else fallback.get("key_requirements", []),
            }
        except (ValueError, TypeError):
            return fallback

    def _fallback_assessment(self, business_profile: dict, grant_structured_data: dict, eligibility_text: str) -> dict:
        reasons = []
        missing = []
        profile_loc = str(business_profile.get("location", "")).upper().strip()
        grant_loc = str(grant_structured_data.get("location", "")).upper().strip()
        criteria_locs = {str(item).upper().strip() for item in grant_structured_data.get("criteria_locations", []) if str(item).strip()}
        if profile_loc and criteria_locs:
            if profile_loc in criteria_locs or "AU" in criteria_locs or "NATIONAL" in criteria_locs:
                reasons.append("Location requirement aligns")
            else:
                return {
                    "eligibility": "NOT_ELIGIBLE",
                    "confidence": 92,
                    "key_reasons": ["Grant location criteria conflicts with business location"],
                    "missing_requirements": [],
                    "recommended_action": "IGNORE",
                }
        elif profile_loc and grant_loc and (profile_loc in grant_loc or grant_loc == "AU"):
            reasons.append("Location requirement aligns")
        else:
            missing.append("Location alignment unclear")

        profile_industries = {str(item).lower().strip() for item in business_profile.get("industry", []) if str(item).strip()}
        criteria_industries = {str(item).lower().strip() for item in grant_structured_data.get("criteria_industries", []) if str(item).strip()}
        if criteria_industries:
            if profile_industries.intersection(criteria_industries):
                reasons.append("Industry requirement aligns")
            else:
                return {
                    "eligibility": "NOT_ELIGIBLE",
                    "confidence": 90,
                    "key_reasons": ["Grant industry criteria conflicts with business industry"],
                    "missing_requirements": [],
                    "recommended_action": "IGNORE",
                }

        count = int(business_profile.get("employee_count", 0) or 0)
        min_size = int(grant_structured_data.get("min_size", 0) or 0)
        max_size = int(grant_structured_data.get("max_size", 10**9) or 10**9)
        if min_size <= count <= max_size:
            reasons.append("Employee count within range")
        else:
            missing.append("Employee count outside range")

        if missing and reasons:
            eligibility = "PARTIAL"
            action = "REVIEW"
            confidence = 55
        elif missing and not reasons:
            eligibility = "NOT_ELIGIBLE"
            action = "IGNORE"
            confidence = 30
        else:
            eligibility = "ELIGIBLE"
            action = "APPLY"
            confidence = 80
        if "must" in eligibility_text.lower() and len(reasons) < 2:
            eligibility = "PARTIAL"
            action = "REVIEW"
            confidence = min(confidence, 60)
        return {
            "eligibility": eligibility,
            "confidence": confidence,
            "key_reasons": reasons or ["Insufficient deterministic evidence"],
            "missing_requirements": missing,
            "recommended_action": action,
        }

    def _coerce_list(self, raw: object, fallback: list[str]) -> list[str]:
        if isinstance(raw, list):
            items = [str(item).strip() for item in raw if str(item).strip()]
            return items if items else fallback
        return fallback
