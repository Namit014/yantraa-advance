import re

class ScoringEngine:
    def score_prompt(self, prompt: str) -> dict:
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())
        
        # Specificity
        specificity = 1
        if word_count > 10: specificity += 1
        if word_count > 20: specificity += 1
        if re.search(r'\d+', prompt): specificity += 1
        if "scara" in prompt_lower or "robot" in prompt_lower: specificity += 1
        specificity = min(5, specificity)
        
        # Completeness
        completeness = 1
        if "payload" in prompt_lower or "kg" in prompt_lower: completeness += 1
        if "reach" in prompt_lower or "mm" in prompt_lower: completeness += 1
        if "axis" in prompt_lower or "dof" in prompt_lower: completeness += 1
        if word_count > 15: completeness += 1
        completeness = min(5, completeness)
        
        # Domain alignment
        domain = 2
        if "robot" in prompt_lower or "arm" in prompt_lower or "scara" in prompt_lower: domain += 2
        domain = min(5, domain)
        
        # Actionability
        actionability = 4
        
        # Scope control
        scope = 2
        if "budget" in prompt_lower or "cost" in prompt_lower: scope += 2
        scope = min(5, scope)
        
        overall = (specificity + completeness + domain + actionability + scope) // 5
        if word_count < 5:
            overall = 2
            
        return {
            "overall": overall,
            "dimensions": {
                "specificity": specificity,
                "completeness": completeness,
                "domain_alignment": domain,
                "actionability": actionability,
                "scope_control": scope
            }
        }
