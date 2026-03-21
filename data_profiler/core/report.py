import os
from typing import Dict, Any, List
from data_profiler.utils.logger import logger

class ReportGenerator:
    """Consolidates all results into final HTML reports."""

    BASE_STYLE = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .status-pass { color: #27ae60; font-weight: bold; }
        .status-fail { color: #e74c3c; font-weight: bold; }
        .score-box { font-size: 2.5em; font-weight: bold; color: #3498db; text-align: center; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
        th { background-color: #f8f9fa; color: #555; }
        tr:hover { background-color: #f1f1f1; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.85em; }
        .badge-pass { background-color: #eafaf1; color: #27ae60; }
        .badge-fail { background-color: #fdedec; color: #e74c3c; }
        .badge-warn { background-color: #fef9e7; color: #f39c12; }
    </style>
    """

    @classmethod
    def generate_schema_html(cls, dataset_name: str, drift_report: Dict[str, Any], actual_schema: Dict[str, Any], output_file: str):
        """Generates report_schema.html."""
        logger.info(f"Generating HTML Schema Report: {output_file}")
        
        type_rows = ""
        for col, info in actual_schema.items():
            type_rows += f"<tr><td>{col}</td><td>{info['source_type']}</td><td>{info['inferred_type']}</td></tr>"

        drift_section = ""
        if drift_report["status"] == "FAIL":
            drift_section = "<h2>Detected Schema Drift</h2><div class='card status-fail'>"
            if drift_report.get("missing_columns"):
                drift_section += f"<p><b>Missing Columns:</b> {', '.join(drift_report['missing_columns'])}</p>"
            if drift_report.get("type_mismatches"):
                drift_mismatch_rows = "".join([f"<tr><td>{m['column']}</td><td>{m['expected']}</td><td>{m['actual']}</td></tr>" for m in drift_report['type_mismatches']])
                drift_section += f"<table><tr><th>Column</th><th>Expected</th><th>Actual</th></tr>{drift_mismatch_rows}</table>"
            drift_section += "</div>"
        else:
            drift_section = "<h2>Schema Drift</h2><p class='status-pass'>No drift detected. Dataset matches expected schema.</p>"

        html = f"""
        <html>
        <head><title>Schema Report - {dataset_name}</title>{cls.BASE_STYLE}</head>
        <body>
            <div class='container'>
                <h1>Schema Analysis: {dataset_name}</h1>
                <div class='card'>
                    <p><b>Status:</b> <span class='{"status-pass" if drift_report["status"] == "PASS" else "status-fail"}'>{drift_report["status"]}</span></p>
                </div>
                {drift_section}
                <h2>Inferred Schema Details</h2>
                <table>
                    <tr><th>Column</th><th>Source Type</th><th>Inferred Type</th></tr>
                    {type_rows}
                </table>
            </div>
        </body>
        </html>
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    @classmethod
    def generate_validations_html(cls, dataset_name: str, scores: Dict[str, float], results: List[Dict[str, Any]], aggregation_results: List[Dict[str, Any]], output_file: str):
        """Generates report_validations.html."""
        logger.info(f"Generating HTML Validations Report: {output_file}")
        
        sections = {
            "primary_key_check": {"title": "Primary Key Integrity", "rows": ""},
            "uniqueness_check": {"title": "Business Keys Uniqueness", "rows": ""},
            "null_check": {"title": "Null Value Checks", "rows": ""},
            "domain_check": {"title": "Domain & Regex Checks", "rows": ""},
            "numeric_check": {"title": "Numeric Range Checks", "rows": ""},
            "date_check": {"title": "Date Format Validation", "rows": ""},
            "schema_type_check": {"title": "Schema Type Validation", "rows": ""},
            "duplicate_row_check": {"title": "Dataset Duplication Analysis", "rows": ""},
            "volume_check": {"title": "Volume & Row Count Checks", "rows": ""},
            "constant_check": {"title": "Constant Value Analysis", "rows": ""},
            "outlier_check": {"title": "Outlier Detection", "rows": ""},
            "empty_string_check": {"title": "Empty String Checks", "rows": ""},
            "schema_drift": {"title": "Schema Drift Alerts", "rows": ""}
        }

        for r in results:
            rtype = r["type"]
            if rtype not in sections:
                # Fallback for any unknown types
                sections[rtype] = {"title": f"{rtype.replace('_', ' ').title()}", "rows": ""}

            if r["status"] == "PASS":
                status_class = "badge-pass"
            elif r["status"] == "WARN":
                status_class = "badge-warn"
            else:
                status_class = "badge-fail"
                
            details = ", ".join([f"{k}: {v}" for k, v in r.items() if k not in ["type", "status", "column", "columns", "mandatory"]])
            mandatory_badge = "<span class='badge badge-pass'>Yes</span>" if r.get("mandatory", True) else "<span class='badge badge-warn'>No</span>"
            col_display = r.get("column") or ", ".join(r.get("columns", []))
            
            sections[rtype]["rows"] += f"<tr><td>{col_display}</td><td>{mandatory_badge}</td><td><span class='badge {status_class}'>{r['status']}</span></td><td>{details}</td></tr>"

        agg_rows = ""
        for r in aggregation_results:
            status_class = "badge-pass" if r["status"] == "PASS" else "badge-fail"
            agg_rows += f"<tr><td>{', '.join(r['groups'])}</td><td><span class='badge {status_class}'>{r['status']}</span></td><td>{r['summary']}</td></tr>"

        sections_html = ""
        for rtype, info in sections.items():
            if info["rows"]:
                sections_html += f"""
                <h2>{info['title']}</h2>
                <table>
                    <tr><th>Target</th><th>Mandatory</th><th>Status</th><th>Details</th></tr>
                    {info['rows']}
                </table>
                """

        html = f"""
        <html>
        <head><title>Validations Report - {dataset_name}</title>{cls.BASE_STYLE}
        <style>
            .score-container {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .score-card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; text-align: center; flex: 1; margin: 0 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .score-card.final {{ border: 2px solid #3498db; background: #f0f8ff; }}
            .score-title {{ font-size: 1.1em; color: #7f8c8d; margin-bottom: 10px; }}
            .score-value {{ font-size: 2.5em; font-weight: bold; color: #2c3e50; }}
            .score-value.fail {{ color: #e74c3c; }}
            .score-value.pass {{ color: #27ae60; }}
        </style>
        </head>
        <body>
            <div class='container'>
                <h1>Data Quality Report: {dataset_name}</h1>
                
                <div class='score-container'>
                    <div class='score-card'>
                        <div class='score-title'>Technical Score</div>
                        <div class='score-value {"pass" if scores.get("technical_score", 0) >= 90 else ("fail" if scores.get("technical_score", 0) < 70 else "")}'>{scores.get('technical_score', 0)}%</div>
                    </div>
                    <div class='score-card final'>
                        <div class='score-title'><b>Final DQ Score</b></div>
                        <div class='score-value {"pass" if scores.get("final_score", 0) >= 90 else ("fail" if scores.get("final_score", 0) < 70 else "")}'>{scores.get('final_score', 0)}%</div>
                    </div>
                    <div class='score-card'>
                        <div class='score-title'>Analytical Score</div>
                        <div class='score-value {"pass" if scores.get("analytical_score", 0) >= 90 else ("fail" if scores.get("analytical_score", 0) < 70 else "")}'>{scores.get('analytical_score', 0)}%</div>
                    </div>
                </div>
                
                {sections_html if sections_html else "<p class='card'>No data validation rules were provided. See the Profiling tab for automated analysis.</p>"}

                {f"<h2>Aggregation Checks</h2><table><tr><th>Groups</th><th>Status</th><th>Sample Summary</th></tr>{agg_rows}</table>" if agg_rows else ""}
            </div>
        </body>
        </html>
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    @classmethod
    def generate_discovery_html(cls, dataset_name: str, discovery_results: Dict[str, Any], output_file: str):
        """Generates report_discovery.html for exploratory insights."""
        logger.info(f"Generating HTML Discovery Report: {output_file}")
        
        # 1. Dataset stats (Always from results['stats'])
        stats = discovery_results.get("stats", {})
        stats_html = ""
        original_rows = discovery_results.get("original_row_count")
        filtered_rows = discovery_results.get("filtered_row_count")
        
        if "total_rows" in stats:
            total_rows = stats['total_rows']
            total_cols = stats['total_cols']
            bytes_val = stats.get('total_size_bytes', 0)
            gb_val = bytes_val / (1024**3)
            tb_val = bytes_val / (1024**4)

            row_display = f"<b style='font-size: 1.5em;'>{total_rows:,}</b>"
            if filtered_rows is not None and original_rows is not None:
                 row_display = f"<b style='font-size: 1.5em;'>{original_rows:,}</b> <span style='color: #7f8c8d; font-size: 0.9em;'>({filtered_rows:,} rows matched filter)</span>"

            stats_html = f"""
            <div class='card' style='display: flex; gap: 40px; justify-content: center; text-align: center;'>
                <div><p style='font-size: 0.9em; color: #7f8c8d; margin: 0;'>Total Rows</p>{row_display}</div>
                <div><p style='font-size: 0.9em; color: #7f8c8d; margin: 0;'>Total Columns</p><b style='font-size: 1.5em;'>{total_cols:,}</b></div>
                <div>
                    <p style='font-size: 0.9em; color: #7f8c8d; margin: 0;'>Dataset Size</p>
                    <div style='display: flex; gap: 15px; justify-content: center; margin-top: 5px;'>
                        <span style='font-size: 1.1em;'><b>{bytes_val:,}</b> <small>Bytes</small></span>
                        <span style='font-size: 1.1em;'><b>{gb_val:.4f}</b> <small>GB</small></span>
                        <span style='font-size: 1.1em;'><b>{tb_val:.6f}</b> <small>TB</small></span>
                    </div>
                </div>
            </div>
            """

        # 1.5 Filter Info (New)
        filter_query = discovery_results.get("filter")
        filtered_sample = discovery_results.get("filtered_sample", [])
        filter_html = ""
        if filter_query:
            sample_table = ""
            if filtered_sample:
                # Get columns from the first record
                cols = list(filtered_sample[0].keys())
                header_row = "".join([f"<th>{c}</th>" for c in cols])
                body_rows = ""
                for row in filtered_sample:
                    row_data = "".join([f"<td>{row.get(c, '')}</td>" for c in cols])
                    body_rows += f"<tr>{row_data}</tr>"
                
                sample_table = f"""
                <div style='margin-top: 15px; overflow-x: auto;'>
                    <p style='font-size: 0.9em; color: #2c3e50; margin-bottom: 5px;'><b>Filtered Data Sample (First {len(filtered_sample)} rows):</b></p>
                    <table style='font-size: 0.85em;'>
                        <thead><tr>{header_row}</tr></thead>
                        <tbody>{body_rows}</tbody>
                    </table>
                </div>
                """

            filter_html = f"""
            <div class='card' style='background-color: #e8f4fd; border-left: 5px solid #3498db;'>
                <p style='margin: 0; color: #2980b9;'><b>🔍 Filter Applied:</b> <code>{filter_query}</code></p>
                <p style='margin: 5px 0 0 0; font-size: 0.85em; color: #7f8c8d;'>Analysis performed on the filtered subset of data.</p>
                {sample_table}
            </div>
            """

        # 2. PK Detection Card
        pk_info = discovery_results.get("primary_key", {"status": "NOT_RUN"})
        pk_html = "<div class='card'>"
        if pk_info["status"] == "SUCCESS":
            pk_html += f"<h3 class='status-pass'>✅ Primary Key Detected</h3><p><b>Columns:</b> {', '.join(pk_info['columns'])}</p><p><b>Uniqueness:</b> {pk_info['distinct_count']} distinct values.</p>"
        elif pk_info["status"] == "NOT_RUN":
            pk_html += f"<h3 style='color: #7f8c8d;'>ℹ️ Discovery Not Executed</h3><p>Run with <code>--check-keys</code> to attempt automatic identification of primary and composite keys.</p>"
        else:
            pk_html += f"<h3 class='status-fail'>❌ No Primary Key Found</h3><p>{pk_info.get('message', 'Automatic detection could not find a unique combination.')}</p>"
        pk_html += "</div>"

        # 3. Distinct Counts Table
        distinct_rows = ""
        for item in pk_info.get("distinct_counts", []):
            distinct_rows += f"<tr><td><code>{item['coluna']}</code></td><td>{item['distinct_count']}</td></tr>"
        
        distinct_table = ""
        if distinct_rows:
            distinct_table = f"""
            <h2>Distinct Values Count (Sorted)</h2>
            <table>
                <tr><th>Column</th><th>Distinct Values</th></tr>
                {distinct_rows}
            </table>
            """

        # 4. Composite History
        history_rows = ""
        for h in pk_info.get("composite_history", []):
            history_rows += f"<tr><td><code>{' + '.join(h['columns'])}</code></td><td>{h['distinct_count']}</td></tr>"
        
        history_table = ""
        if history_rows:
            history_table = f"""
            <h2>Composite Key Search History</h2>
            <p style='font-size: 0.9em; color: #7f8c8d;'>Order of attempt based on highest cardinality combinations.</p>
            <table>
                <tr><th>Column Combination</th><th>Combined Distinct Values</th></tr>
                {history_rows}
            </table>
            """
        # 5. Deduplication Analysis (New)
        dedup_html = ""
        dedup_results = discovery_results.get("deduplication", [])
        if dedup_results:
            dedup_html = "<h2>Deduplication Analysis</h2>"
            for res in dedup_results:
                status_class = "status-pass" if res["duplicate_count"] == 0 else "status-fail"
                
                col_info = f"<p><b>Checked Columns:</b> {', '.join(res['columns'])}</p>"
                if res.get("excluded_columns"):
                    col_info += f"<p><b>Excluded from check:</b> {', '.join(res['excluded_columns'])}</p>"
                
                dedup_html += f"""
                <div class='card'>
                    <h3 class='{status_class}'>🔍 {res['label']}</h3>
                    {col_info}
                    <p><b>Duplicates Found:</b> {res['duplicate_count']} ({res['duplicate_percent']}%)</p>
                </div>
                """
                
            # Semantic Risk Component
            semantic_risk_html = ""
            risk_info = discovery_results.get("semantic_risk")
            if risk_info:
                risk_level = risk_info["risk_level"]
                bg_color = "#fef9e7" if risk_level == "MEDIUM" else ("#fdedec" if risk_level == "HIGH" else "#eafaf1")
                border_color = "#f39c12" if risk_level == "MEDIUM" else ("#e74c3c" if risk_level == "HIGH" else "#27ae60")
                risk_icon = "⚠️" if risk_level in ["MEDIUM", "HIGH"] else "✅"
                
                false_uq_html = ""
                if risk_info.get("false_uniqueness"):
                    false_uq_html = f"<div style='margin-top:10px; padding: 10px; background: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px;'><p style='color: #856404; margin: 0;'><b>🚨 Semantic Alert: False Uniqueness Detected!</b> The technical primary key is unique, but business identifiers contain duplicates. This indicates a high risk of <b>Metric Inflation</b> in downstream BI tools.</p></div>"
                
                semantic_risk_html = f"""
                <h2>Semantic Risk Analysis</h2>
                <div class='card' style='background-color: {bg_color}; border-left: 5px solid {border_color};'>
                    <h3 style='margin-top: 0;'>{risk_icon} Risk Level: {risk_level}</h3>
                    <p><b>Maximum Business Duplication:</b> {risk_info['max_duplicate_percent']}%</p>
                    {false_uq_html}
                </div>
                """
                dedup_html = semantic_risk_html + dedup_html

        # 6. Discovery Group Analysis (Simplified JSON feature)
        group_html = ""
        for group in discovery_results.get("group_analysis", []):
            group_cols = " + ".join(group["columns"])
            group_rows = ""
            for item in group["data"]:
                group_rows += f"<tr><td>{item['values']}</td><td>{item['count']}</td><td>{item['percent']:.2f}%</td></tr>"
            
            group_html += f"""
            <h3>🔍 Group Distribution: {group_cols}</h3>
            <table>
                <tr><th>Value Combination</th><th>Record Count</th><th>Percentage</th></tr>
                {group_rows}
            </table>
            <br>
            """

        date_html = ""
        for d in discovery_results.get("dates", []):
            date_html += f"<div class='card'><h3>📅 Date Analysis: {d['column']}</h3><p><b>Max Date:</b> {d['max_date']}</p>"
            if d.get("distribution"):
                rows = "".join([f"<tr><td>{item['date']}</td><td>{item['count']}</td></tr>" for item in d["distribution"]])
                date_html += f"<table><tr><th>Date</th><th>Record Count</th></tr>{rows}</table>"
            date_html += "</div>"

        html = f"""
        <html>
        <head><title>Discovery Insights - {dataset_name}</title>{cls.BASE_STYLE}</head>
        <body>
            <div class='container'>
                <h1>Discovery Insights: {dataset_name}</h1>
                {stats_html}
                {distinct_table}
                <h2>Primary Key Detection</h2>
                {pk_html}
                {history_table}
                {dedup_html}
                {group_html}
                {filter_html}
                {f"<h2>Date Distributions</h2>{date_html}" if date_html else ""}
            </div>
        </body>
        </html>
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    @classmethod
    def generate_dashboard_html(cls, dataset_name: str, schema_report: str, validations_report: str, profiling_report: str, discovery_report: str, output_file: str):
        """Generates a unified landing page with tabs for all reports."""
        logger.info(f"Generating Unified Dashboard: {output_file}")
        
        # We use basenames for the iframes assuming they are in the same directory
        schema_file = os.path.basename(schema_report)
        validations_file = os.path.basename(validations_report)
        profiling_file = os.path.basename(profiling_report)
        discovery_file = os.path.basename(discovery_report)
        drift_file = "report_drift.html" # Fixed name per drift module

        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Data Quality Dashboard - {dataset_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
        header {{ background-color: #2c3e50; color: white; padding: 1rem; text-align: center; }}
        nav {{ display: flex; background-color: #34495e; }}
        nav button {{ flex: 1; padding: 1rem; color: white; background: none; border: none; cursor: pointer; font-size: 1rem; transition: background 0.3s; }}
        nav button:hover {{ background-color: #2c3e50; }}
        nav button.active {{ background-color: #1abc9c; font-weight: bold; }}
        section {{ display: none; padding: 0; background-color: white; height: calc(100vh - 150px); overflow: hidden; }}
        section iframe {{ width: 100%; height: 100%; border: none; }}
    </style>
</head>
<body>

<header>
    <h1>Data Quality Dashboard: {dataset_name}</h1>
</header>

<nav>
    <button class="tab-button" data-tab="schema">Schema</button>
    <button class="tab-button" data-tab="validations">Validations</button>
    <button class="tab-button active" data-tab="discovery">Discovery</button>
    <button class="tab-button" data-tab="drift">Drift</button>
    <button class="tab-button" data-tab="profiling">Profiling</button>
</nav>

<section id="schema">
    <iframe src="{schema_file}"></iframe>
</section>

<section id="validations">
    <iframe src="{validations_file}"></iframe>
</section>

<section id="discovery" style="display:block;">
    <iframe src="{discovery_file}"></iframe>
</section>

<section id="drift">
    <iframe src="{drift_file}"></iframe>
</section>

<section id="profiling">
    <iframe src="{profiling_file}"></iframe>
</section>

<script>
    const buttons = document.querySelectorAll('.tab-button');
    const sections = document.querySelectorAll('section');

    buttons.forEach(button => {{
        button.addEventListener('click', () => {{
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            const tab = button.getAttribute('data-tab');
            sections.forEach(sec => {{
                sec.style.display = (sec.id === tab) ? 'block' : 'none';
            }});
        }});
    }});
</script>

</body>
</html>
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
