import pandas as pd
from utils.ollama_setup import run_inference_on_document

from typing import List, Dict, Any
from core.database.operations import save_analysis
from core.database.session import get_session

class AnalysisService:
    @staticmethod
    def analyze_documents(
        user_id: str,
        documents: List[Dict[str, Any]],
        instructions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        session = get_session()
        
        try:
            for doc in documents:
                # Run analysis using Ollama or other inference engine
                response = run_inference_on_document(doc["content"], instructions)
                
                # Save analysis results
                analysis = save_analysis(
                    session=session,
                    user_id=user_id,
                    extraction_id=doc["extraction_id"],
                    instructions=instructions,
                    results=response
                )
                
                results.append({
                    "file_name": doc["file_name"],
                    "data": response
                })
                
        finally:
            session.close()
        
        return results

    @staticmethod
    def format_results(results: List[Dict[str, Any]], instructions: List[Dict[str, Any]]) -> pd.DataFrame:
        df_data = []
        for result in results:
            row = {"File Name": result["file_name"]}
            data = result["data"]
            if data:
                for instruction in instructions:
                    title = instruction["title"]
                    formatted_title = title.lower().replace(" ", "_")
                    row[title] = data.get(formatted_title)
            df_data.append(row)
        return pd.DataFrame(df_data)