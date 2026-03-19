import pandas as pd
from ydata_profiling import ProfileReport
from data_profiler.utils.logger import logger
from data_profiler.utils.sql_utils import apply_sql_filter

class ProfilingEngine:
    """Integration with ydata-profiling for deep data analysis."""

    @staticmethod
    def generate_report(df: pd.DataFrame, output_file: str = "report.html", title: str = "Data Profiling Report", filter_query: str = None) -> str:
        """Generates an HTML profiling report."""
        try:
            if filter_query:
                df = apply_sql_filter(df, filter_query)
                
            logger.info(f"Generating profiling report: {output_file}")
            profile = ProfileReport(df, title=title, explorative=True)
            profile.to_file(output_file)
            return output_file
        except Exception as e:
            logger.error(f"Error generating profiling report: {e}")
            return ""
