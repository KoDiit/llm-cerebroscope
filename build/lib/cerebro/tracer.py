import ollama

class CerebroTracer:
    def __init__(self):
        pass

    def analyze_query(self, query, chunks, model_name="llama3"):
        """
        Generates an answer based on retrieved chunks using the specified model.
        """
        # Prepare context with IDs for citation
        context_text = "\n\n".join([c.to_context_format() for c in chunks])
        
        prompt = (
            "You are an elite Forensic Data Analyst. "
            "Your goal is to answer the user's query strictly based on the provided CONTEXT. "
            "Rules:\n"
            "1. You MUST cite your sources using the format [ID: xxxxxxxx].\n"
            "2. If sources conflict, mention the conflict but prioritize the one marked as NEWER in the dates.\n"
            "3. Be concise and professional.\n"
            "4. If the context does not contain the answer, state that clearly."
        )

        try:
            response = ollama.chat(
                model=model_name, # Use the dynamic model
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"QUERY: {query}\n\nEVIDENCE CONTEXT:\n{context_text}"}
                ]
            )
            return response['message']['content']
        except Exception as e:
            return f"❌ AI Error ({model_name}): {str(e)}"