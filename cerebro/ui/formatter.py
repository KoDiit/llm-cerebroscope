from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.progress import BarColumn, Progress
import re

console = Console()

class CerebroFormatter:
    @staticmethod
    def display_investigation(query, response):
        console.print(f"\n[bold cyan]🔍 LLM-CEREBROSCOPE INVESTIGATION[/bold cyan]")
        console.print(f"[bold]Query:[/bold] {query}")
        
        rich_text = Text()
        parts = re.split(r"(\[ID: .*?\])", response)
        
        for part in parts:
            if part.startswith("[ID:"):
                rich_text.append(part, style="bold green")
            else:
                rich_text.append(part)
        
        console.print(Panel(rich_text, title="Evidence-Based Response", border_style="blue"))

    @staticmethod
    def highlight_relevance(retrieved_chunks, used_ids, validator=None):
        """
        Visualizes the Heatmap with Reliability Scores in CLI.
        Now supports an optional 'validator' to calculate scores dynamically.
        """
        console.print("\n[bold]🌡️  CONTEXT HEATMAP & RELIABILITY SCORES:[/bold]")
        
        for chunk in retrieved_chunks:
            # Check usage
            is_used = any(uid in chunk.chunk_id for uid in used_ids)
            
            # Calculate Score if validator is provided
            score = 0
            if validator:
                score = validator.calculate_reliability_score(chunk)
            
            # Styles
            if is_used:
                style = "bold green"
                status_icon = "[V] USED   "
            else:
                style = "bright_black"
                status_icon = "[X] IGNORED"
            
            # Score Color
            score_color = "green" if score > 70 else "yellow" if score > 40 else "red"
            
            # Build the visual line
            snippet = chunk.text[:70].replace("\n", " ")
            
            # Print Info
            console.print(f"[{style}]{status_icon} | ID: {chunk.chunk_id} | {snippet}...[/{style}]")
            
            # Print Mini Bar for Score
            if validator:
                console.print(f"            ↳ Reliability: [{score_color}]{score}/100[/{score_color}] " + "█" * (score // 5))

    @staticmethod
    def display_recommendation(recommendation_text):
        console.print(Panel(
            recommendation_text, 
            title="🎯 CEREBRO ANALYTICAL VERDICT", 
            border_style="gold1",
            padding=(1, 2)
        ))