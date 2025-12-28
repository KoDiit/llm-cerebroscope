import os
import time

class CerebroReporter:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def save_report(self, query, answer, conflicts, retrieved_chunks):
        """Generates a Markdown report for the investigation."""
        
        # Create a unique filename based on time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # Sanitize filename (remove illegal chars)
        sanitized_query = "".join([c if c.isalnum() else "_" for c in query])[:30]
        filename = f"{self.output_dir}/Investigation_{timestamp}_{sanitized_query}.md"

        # Prepare formatted conflicts string safely (fixing the SyntaxError)
        formatted_conflicts = conflicts.replace('\n', '\n> ')

        with open(filename, "w", encoding="utf-8") as f:
            # 1. Header
            f.write(f"# 🕵️ CerebroScope Investigation Report\n")
            f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Query:** {query}\n\n")
            
            # 2. The Verdict (Logical Analysis)
            f.write(f"## ⚠️ Logical Validation & Conflicts\n")
            f.write(f"> {formatted_conflicts}\n\n")

            # 3. The Answer
            f.write(f"## 🧠 AI Analysis\n")
            f.write(f"{answer}\n\n")

            # 4. Evidence Locker (Source Material)
            f.write(f"## 📂 Evidence Locker (Retrieved Context)\n")
            f.write("| ID | Source | Date | Preview |\n")
            f.write("|---|---|---|---|\n")
            
            for chunk in retrieved_chunks:
                # Safely get timestamp
                ts = getattr(chunk, 'timestamp', 0)
                chunk_date = time.strftime('%Y-%m-%d', time.localtime(ts))
                
                # Clean text for table (remove newlines and pipes)
                clean_text = chunk.text.replace("\n", " ").replace("|", " ")[:100] + "..."
                f.write(f"| `{chunk.chunk_id}` | {chunk.source} | {chunk_date} | {clean_text} |\n")

        return filename