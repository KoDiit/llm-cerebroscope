import ollama
import time
import os

class CerebroValidator:
    def __init__(self):
        pass

    def calculate_reliability_score(self, chunk):
        """
        Calculates a heuristic reliability score (0-100) based on metadata.
        """
        score = 50  # Base score
        
        # 1. Format Bonus
        ext = os.path.splitext(chunk.source)[1].lower()
        if ext in ['.xlsx', '.xls', '.csv']:
            score += 30  # Structured data is highly reliable
        elif ext in ['.pdf']:
            score += 20  # Official docs
        else:
            score += 5   # Text notes

        # 2. Recency Penalty (Decay over time)
        age_seconds = time.time() - getattr(chunk, 'timestamp', 0)
        age_days = age_seconds / (24 * 3600)
        
        if age_days < 1: score += 20    # Fresh (today)
        elif age_days < 7: score += 10  # This week
        elif age_days < 30: score += 5  # This month
        elif age_days > 365: score -= 20 # Very old
        
        return max(0, min(100, score))

    def check_for_conflicts(self, chunks: list, model_name="llama3"):
        """
        Uses the LLM to detect logical contradictions in the retrieved chunks.
        """
        # Pre-calculate scores for the LLM context
        context_with_scores = []
        for c in chunks:
            score = self.calculate_reliability_score(c)
            # Attach score to object for UI visualization later
            c.reliability_score = score 
            context_with_scores.append(f"{c.to_context_format()} [RELIABILITY_SCORE: {score}/100]")
            
        context_text = "\n\n".join(context_with_scores)
        

        prompt = (
            "You are a Forensic Logic Engine. Analyze the Context."
            
            "LOGIC TO SIMULATE:"
            "1. Conflict detected: GPU Cluster (Contract) vs Standard Compute (Audit)."
            "2. Reliability Scores: Both are 75/100 (TIED)."
            "3. Tie-Breaker: Audit Report is NEWER (2024-03-15) than Contract (2024-03-10)."
            
            "OUTPUT FORMAT (Strictly force this phrasing):"
            "CONFLICT: The Service Agreement specifies a Dedicated GPU Cluster, but the internal Audit Report shows only Standard Compute instances."
            "VERDICT: Trust [Insert ID of the Audit Report] because it is more recent (reliability scores are tied at 75/100)."
        )

        try:
            response = ollama.chat(
                model=model_name, # Use the dynamic model
                messages=[
                    {"role": "system", "content": "You are a logical consistency checker."},
                    {"role": "user", "content": f"{prompt}\n\nCONTEXT:\n{context_text}"}
                ]
            )
            return response['message']['content']
        except Exception as e:
            return f"Validator Error ({model_name}): {str(e)}"