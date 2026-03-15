import pandas as pd
from ydata_profiling import ProfileReport
from data_profiler.utils.logger import logger

class ProfilingEngine:
    """Integration with ydata-profiling for deep data analysis."""

    @staticmethod
    def generate_report(df: pd.DataFrame, output_file: str = "report.html", title: str = "Data Profiling Report") -> str:
        """Generates an HTML profiling report."""
        try:
            logger.info(f"Generating profiling report: {output_file}")
            profile = ProfileReport(df, title=title, explorative=True)
            profile.to_file(output_file)
            return output_file
        except Exception as e:
            logger.error(f"Error generating profiling report: {e}")
            return ""
