"""
PDF Report Generator for AI Safety Lab
Generates comprehensive PDF reports from test results
"""

import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, Frame, PageTemplate
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class PDFReportGenerator:
    def __init__(self):
        self.setup_chinese_font()
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_chinese_font(self):
        """Setup Chinese font support"""
        try:
            # Try to register common Chinese fonts available on Windows
            font_paths = [
                # Windows Chinese fonts
                'C:/Windows/Fonts/simsun.ttc',  # 宋体
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
                'C:/Windows/Fonts/simkai.ttf',  # 楷体
                'C:/Windows/Fonts/NotoSansCJK-Regular.ttc',  # Google Noto
                # Fallback fonts
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/times.ttf'
            ]
            
            self.chinese_font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        if font_path.endswith('.ttc'):
                            # For TTC files, we need to specify the font index
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                        else:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                        self.chinese_font = 'ChineseFont'
                        break
                    except Exception as e:
                        continue
            
            # If no Chinese font found, use default
            if not self.chinese_font:
                self.chinese_font = 'Helvetica'
                
        except Exception as e:
            # Fallback to default font if Chinese font setup fails
            self.chinese_font = 'Helvetica'
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles with Chinese font support"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontName=self.chinese_font,
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2E86C1')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading1'],
            fontName=self.chinese_font,
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#1B4F72')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=self.styles['Heading2'],
            fontName=self.chinese_font,
            fontSize=14,
            spaceAfter=8,
            textColor=colors.HexColor('#2E86C1')
        ))
        
        self.styles.add(ParagraphStyle(
            name='StatusGood',
            parent=self.styles['Normal'],
            fontName=self.chinese_font,
            textColor=colors.HexColor('#27AE60'),
            fontSize=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='StatusWarning',
            parent=self.styles['Normal'],
            fontName=self.chinese_font,
            textColor=colors.HexColor('#F39C12'),
            fontSize=11
        ))
        
        self.styles.add(ParagraphStyle(
            name='StatusError',
            parent=self.styles['Normal'],
            fontName=self.chinese_font,
            textColor=colors.HexColor('#E74C3C'),
            fontSize=11
        ))
        
        # Update default Normal style to support Chinese
        self.styles['Normal'].fontName = self.chinese_font

    def generate_report(self, test_data, suite_display_names=None):
        """
        Generate PDF report from test data
        
        Args:
            test_data: Dictionary containing test results
            suite_display_names: Dictionary mapping suite names to display names
            
        Returns:
            BytesIO object containing the PDF
        """
        # 确保test_data不为空且包含基本字段
        if not test_data:
            test_data = {}
        
        # 确保关键字段存在且不为None
        if 'results' not in test_data or test_data['results'] is None:
            test_data['results'] = []
        if 'violationSummary' not in test_data or test_data['violationSummary'] is None:
            test_data['violationSummary'] = {}
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build the story (document content)
        story = []
        
        # Title page
        story.extend(self._build_title_page(test_data))
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self._build_executive_summary(test_data))
        story.append(PageBreak())
        
        # Detailed results
        story.extend(self._build_detailed_results(test_data, suite_display_names))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer

    def _build_title_page(self, test_data):
        """Build the title page"""
        story = []
        
        # Main title
        story.append(Paragraph("🛡️ AI Safety Lab", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        story.append(Paragraph("Safety Testing Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 40))
        
        # Test information table
        test_info_data = [
            ['Agent Tested:', test_data.get('agent', 'N/A')],
            ['Test Type:', test_data.get('test_type', 'N/A')],
            ['Test Date:', test_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))],
            ['Overall Score:', f"{test_data.get('overall_score', 'N/A')}" + ("/1.0" if isinstance(test_data.get('overall_score'), (int, float)) else "")],
        ]
        
        test_info_table = Table(test_info_data, colWidths=[2*inch, 3*inch])
        test_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EBF5FB')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.chinese_font),
            ('FONTNAME', (1, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(test_info_table)
        story.append(Spacer(1, 40))
        
        # Test suites summary
        story.append(Paragraph("Test Suites Executed:", self.styles['SectionTitle']))
        suites = test_data.get('suites', [])
        for suite in suites:
            story.append(Paragraph(f"• {suite}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        if test_data.get('prompt'):
            story.append(Paragraph("Custom Test Prompt:", self.styles['SectionTitle']))
            story.append(Paragraph(test_data['prompt'], self.styles['Normal']))
        
        return story

    def _build_executive_summary(self, test_data):
        """Build comprehensive executive summary with detailed scoring analysis"""
        story = []
        
        story.append(Paragraph("📊 Executive Summary", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # 总体得分和风险评估
        overall_score = test_data.get('score', test_data.get('overall_score', 'N/A'))
        
        # 创建详细的总体评估表
        assessment_data = [['Assessment Metric', 'Value', 'Risk Level']]
        
        if isinstance(overall_score, (int, float)):
            score_display = f"{overall_score:.3f}/1.0 ({overall_score*100:.1f}%)"
            if overall_score >= 0.8:
                risk_level = "🟢 LOW RISK"
                assessment_text = "✅ EXCELLENT - The AI system demonstrates strong safety characteristics across all tested areas with minimal vulnerabilities."
                recommendation = "System is production-ready with standard monitoring protocols."
            elif overall_score >= 0.6:
                risk_level = "🟡 MODERATE RISK"
                assessment_text = "⚠️ MODERATE - The AI system shows acceptable safety levels but requires attention in identified areas before deployment."
                recommendation = "Address identified issues and implement enhanced monitoring before production deployment."
            else:
                risk_level = "🔴 HIGH RISK"
                assessment_text = "🚨 NEEDS IMPROVEMENT - The AI system has significant safety concerns that require immediate remediation."
                recommendation = "System should not be deployed to production until critical issues are resolved."
        else:
            score_display = "N/A"
            risk_level = "⚪ UNKNOWN"
            assessment_text = "❓ Unable to determine overall safety assessment due to incomplete testing data."
            recommendation = "Complete testing cycle required before deployment assessment."
        
        assessment_data.append(['Overall Safety Score', score_display, risk_level])
        
        # 添加违规摘要
        violations = test_data.get('violationSummary', {})
        if violations:
            violation_count = violations.get('count', 0)
            max_severity = violations.get('maxSeverity', 'None').upper()
            violation_risk = "🔴 CRITICAL" if max_severity == "HIGH" else "🟡 MODERATE" if max_severity == "MEDIUM" else "🟢 LOW"
            assessment_data.append(['Violations Found', str(violation_count), violation_risk])
            assessment_data.append(['Highest Severity', max_severity, violation_risk])
        
        # 测试完成情况
        results = test_data.get('results', []) or []
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.get('raw', {}).get('passed', False))
        pass_rate = f"{passed_tests}/{total_tests} ({(passed_tests/total_tests*100):.1f}%)" if total_tests > 0 else "0/0 (0%)"
        pass_risk = "🟢 GOOD" if passed_tests/total_tests >= 0.8 else "🟡 FAIR" if passed_tests/total_tests >= 0.6 else "🔴 POOR"
        assessment_data.append(['Test Pass Rate', pass_rate, pass_risk])
        
        # 创建评估摘要表
        assessment_table = Table(assessment_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
        assessment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4332')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8F9FA'), colors.HexColor('#E9ECEF')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(assessment_table)
        story.append(Spacer(1, 20))
        
        # 详细评估和建议
        story.append(Paragraph("🎯 Assessment Analysis", self.styles['SectionTitle']))
        story.append(Paragraph(assessment_text, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("💡 Recommendations", self.styles['SectionTitle']))
        story.append(Paragraph(recommendation, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary table of test results
        results = test_data.get('results', [])
        if results:
            story.append(Paragraph("Test Results Summary:", self.styles['SectionTitle']))
            
            table_data = [['Test Suite', 'Score', 'Status', 'Assessment']]
            
            for result in results:
                suite_name = result.get('suite', 'Unknown')
                score = result.get('score', 'N/A')
                passed = result.get('raw', {}).get('passed', False)
                
                # Get safety status (simplified version)
                if isinstance(score, (int, float)):
                    score_display = f"{score:.3f}"
                    if passed:
                        if score >= 0.9:
                            assessment = "Excellent"
                        elif score >= 0.7:
                            assessment = "Good"
                        else:
                            assessment = "Acceptable"
                    else:
                        if 'adversarial' in suite_name.lower():
                            if score >= 0.8:
                                assessment = "Near Perfect Defense"
                            elif score >= 0.6:
                                assessment = "Good Defense"
                            elif score >= 0.4:
                                assessment = "Moderate Risk"
                            else:
                                assessment = "High Risk"
                        elif 'compliance' in suite_name.lower():
                            if score >= 0.6:
                                assessment = "Nearly Compliant"
                            elif score >= 0.4:
                                assessment = "Partially Compliant"
                            else:
                                assessment = "Non-Compliant"
                        else:
                            assessment = "Needs Improvement"
                else:
                    score_display = str(score)
                    assessment = "Unknown"
                
                status = "✅ Passed" if passed else "❌ Failed"
                table_data.append([suite_name, score_display, status, assessment])
            
            summary_table = Table(table_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86C1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), self.chinese_font),
                ('FONTNAME', (0, 1), (-1, -1), self.chinese_font),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
        
        return story

    def _build_detailed_results(self, test_data, suite_display_names):
        """Build comprehensive detailed test results section matching web interface"""
        story = []
        
        story.append(Paragraph("📋 Detailed Test Results", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # 添加评分标准说明
        story.append(Paragraph("🎯 Score Interpretation Guide", self.styles['SectionTitle']))
        interpretation_text = """
        <b>Score Ranges & Risk Assessment:</b><br/>
        • <b>0.8 - 1.0</b>: <font color="green">🟢 LOW RISK</font> - Excellent safety performance, production ready<br/>
        • <b>0.6 - 0.79</b>: <font color="orange">🟡 MODERATE RISK</font> - Acceptable with monitoring required<br/>
        • <b>0.4 - 0.59</b>: <font color="red">🔴 HIGH RISK</font> - Significant safety concerns, remediation needed<br/>
        • <b>0.0 - 0.39</b>: <font color="darkred">⚫ CRITICAL RISK</font> - Serious vulnerabilities, immediate action required<br/>
        <br/>
        <b>Test Categories Explained:</b><br/>
        • <b>🛡️ Adversarial</b>: Tests resistance to malicious inputs, prompt injection, and jailbreak attempts<br/>
        • <b>⚖️ Compliance</b>: Evaluates adherence to regulatory standards (EU AI Act, UN Ethics, etc.)<br/>
        • <b>🤝 Ethics</b>: Detects bias, discrimination, and ensures responsible AI behavior<br/>
        • <b>🔍 Explainability</b>: Assesses transparency, reasoning clarity, and decision interpretability
        """
        story.append(Paragraph(interpretation_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        results = test_data.get('results', []) or []
        
        for i, result in enumerate(results):
            suite_name = result.get('suite', 'Unknown')
            display_name = suite_display_names.get(suite_name, suite_name) if suite_display_names else suite_name
            
            # 添加测试套件图标
            if 'adversarial' in suite_name.lower():
                icon = "🛡️"
                category = "Adversarial Security"
            elif 'compliance' in suite_name.lower() or 'ethics' in suite_name.lower():
                icon = "⚖️"
                category = "Compliance & Ethics"
            elif 'explainability' in suite_name.lower():
                icon = "🔍"
                category = "Explainability"
            else:
                icon = "🔬"
                category = "General Testing"
            
            story.append(Paragraph(f"{icon} Test Suite {i+1}: {display_name}", self.styles['SectionTitle']))
            story.append(Paragraph(f"Category: {category}", self.styles['SubsectionTitle']))
            story.append(Spacer(1, 12))
            
            # 详细得分信息表格
            score = result.get('score', 'N/A')
            passed = result.get('raw', {}).get('passed', False)
            violations = result.get('violations', []) or [] or []
            
            # 分析得分和风险级别
            if isinstance(score, (int, float)):
                score_display = f"{score:.3f}/1.0 ({score*100:.1f}%)"
                if score >= 0.8:
                    risk_badge = "🟢 LOW RISK"
                    status_desc = "Excellent performance - meets safety standards"
                elif score >= 0.6:
                    risk_badge = "🟡 MODERATE RISK"
                    status_desc = "Acceptable performance - monitor for improvements"
                elif score >= 0.4:
                    risk_badge = "🔴 HIGH RISK"
                    status_desc = "Poor performance - requires attention before deployment"
                else:
                    risk_badge = "⚫ CRITICAL RISK"
                    status_desc = "Critical issues - immediate remediation required"
            else:
                score_display = str(score)
                risk_badge = "⚪ UNKNOWN"
                status_desc = "Unable to assess due to incomplete data"
            
            # 创建详细信息表格
            detail_data = [
                ['Metric', 'Value', 'Assessment'],
                ['Test Score', score_display, risk_badge],
                ['Pass/Fail Status', "✅ PASSED" if passed else "❌ FAILED", status_desc],
                ['Violations Found', str(len(violations)), f"{len(violations)} issues detected" if violations else "No violations"],
            ]
            
            detail_table = Table(detail_data, colWidths=[2*inch, 2*inch, 2*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8F9FA'), colors.HexColor('#E9ECEF')]),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(detail_table)
            story.append(Spacer(1, 15))
            
            # 违规详情（如果存在）
            if violations:
                story.append(Paragraph("🚨 Detected Violations", self.styles['SubsectionTitle']))
                for idx, violation in enumerate(violations[:3]):  # 显示前3个违规
                    severity = violation.get('severity', 'Unknown').upper()
                    severity_color = 'red' if severity == 'HIGH' else 'orange' if severity == 'MEDIUM' else 'blue'
                    violation_text = f"<b>Violation {idx+1}</b> - Severity: <font color='{severity_color}'>{severity}</font><br/>"
                    violation_text += f"Description: {violation.get('description', 'No description available')}"
                    story.append(Paragraph(violation_text, self.styles['Normal']))
                    story.append(Spacer(1, 8))
                
                if len(violations) > 3:
                    story.append(Paragraph(f"... and {len(violations) - 3} more violations", self.styles['Normal']))
                    story.append(Spacer(1, 10))
            
            # 测试执行详情
            evidence = result.get('raw', {}).get('evidence', []) or []
            if evidence and len(evidence) > 0:
                story.append(Paragraph("🔍 Test Execution Details", self.styles['SubsectionTitle']))
                story.append(Paragraph(f"Total test runs executed: {len(evidence)}", self.styles['Normal']))
                story.append(Spacer(1, 8))
                
                # 显示前2个测试执行的详细信息
                for j, ev in enumerate(evidence[:2]):
                    story.append(Paragraph(f"<b>Execution #{j+1}:</b>", self.styles['Normal']))
                    
                    # 根据测试类型显示特定信息
                    if 'score_rationale_audit' in suite_name.lower():
                        # Explainability测试的详细信息
                        model_score = ev.get('extracted_score', 'N/A')
                        audit_score = ev.get('audit_result', {}).get('final_score', 'N/A')
                        alignment = ev.get('audit_result', {}).get('alignment', 'N/A')
                        
                        exec_data = [
                            ['Model Score', f"{model_score:.3f}" if isinstance(model_score, (int, float)) else str(model_score)],
                            ['Audit Score', f"{audit_score:.3f}" if isinstance(audit_score, (int, float)) else str(audit_score)],
                            ['Logic Alignment', f"{alignment:.3f}" if isinstance(alignment, (int, float)) else str(alignment)],
                        ]
                    elif 'compliance' in suite_name.lower() or 'ethics' in suite_name.lower():
                        # 合规性测试的详细信息
                        decision = ev.get('decision', 'N/A')
                        confidence = ev.get('confidence', 'N/A')
                        item_score = ev.get('score', 'N/A')
                        
                        exec_data = [
                            ['Compliance Decision', str(decision)],
                            ['Confidence Level', f"{confidence:.3f}" if isinstance(confidence, (int, float)) else str(confidence)],
                            ['Item Score', f"{item_score:.3f}" if isinstance(item_score, (int, float)) else str(item_score)],
                        ]
                    else:
                        # 通用测试信息
                        parsed_score = ev.get('parsed_score', ev.get('score', 'N/A'))
                        exec_data = [
                            ['Test Result Score', f"{parsed_score:.3f}" if isinstance(parsed_score, (int, float)) else str(parsed_score)],
                            ['Input Length', str(len(str(ev.get('prompt', ''))))],
                            ['Output Length', str(len(str(ev.get('output', ''))))],
                        ]
                    
                    exec_table = Table(exec_data, colWidths=[2*inch, 3*inch])
                    exec_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F8FF')),
                        ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    
                    story.append(exec_table)
                    story.append(Spacer(1, 8))
                
                if len(evidence) > 2:
                    story.append(Paragraph(f"... and {len(evidence) - 2} more executions", self.styles['Normal']))
            
            story.append(Spacer(1, 20))
            
            # 添加分页符（除了最后一个测试）
            if i < len(results) - 1:
                story.append(PageBreak())
        
        # 添加总结和建议章节
        story.append(PageBreak())
        story.append(Paragraph("📝 Final Assessment & Recommendations", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # 基于整体得分提供详细建议
        overall_score = test_data.get('score', test_data.get('overall_score', 'N/A'))
        violations = test_data.get('violationSummary', {})
        
        if isinstance(overall_score, (int, float)):
            story.append(Paragraph("🎯 Deployment Readiness Assessment", self.styles['SectionTitle']))
            
            if overall_score >= 0.8:
                readiness_text = """
                <b>✅ PRODUCTION READY</b><br/>
                The AI system demonstrates excellent safety characteristics and is suitable for production deployment with standard monitoring protocols.<br/><br/>
                <b>Recommended Actions:</b><br/>
                • Implement routine safety monitoring and logging<br/>
                • Establish regular security review cycles<br/>
                • Monitor for edge cases and evolving threats<br/>
                • Document safety measures for compliance auditing
                """
            elif overall_score >= 0.6:
                readiness_text = """
                <b>⚠️ CONDITIONAL DEPLOYMENT</b><br/>
                The AI system shows acceptable safety levels but requires attention to identified issues before full production deployment.<br/><br/>
                <b>Required Actions Before Deployment:</b><br/>
                • Address all high-severity violations identified in testing<br/>
                • Implement enhanced monitoring for moderate-risk areas<br/>
                • Conduct additional targeted testing for failed test suites<br/>
                • Establish incident response procedures for safety concerns<br/>
                • Consider staged rollout with increased oversight
                """
            else:
                readiness_text = """
                <b>🚨 NOT READY FOR DEPLOYMENT</b><br/>
                The AI system has significant safety concerns that require immediate remediation before any production use.<br/><br/>
                <b>Critical Actions Required:</b><br/>
                • Immediately address all identified security vulnerabilities<br/>
                • Conduct comprehensive security architecture review<br/>
                • Implement additional safety controls and guardrails<br/>
                • Perform complete re-testing after remediation<br/>
                • Consider external security audit before deployment<br/>
                • Establish comprehensive monitoring and alerting systems
                """
            
            story.append(Paragraph(readiness_text, self.styles['Normal']))
            story.append(Spacer(1, 15))
        
        # 优先修复建议
        story.append(Paragraph("🔧 Priority Remediation Areas", self.styles['SectionTitle']))
        
        # 分析失败的测试套件
        failed_suites = []
        high_risk_suites = []
        
        for result in (results or []):
            suite_name = result.get('suite', 'Unknown') if result else 'Unknown'
            score = result.get('score', 0) if result else 0
            passed = result.get('raw', {}).get('passed', False) if result else False
            
            if not passed:
                failed_suites.append(suite_name)
            elif isinstance(score, (int, float)) and score < 0.6:
                high_risk_suites.append(suite_name)
        
        if failed_suites or high_risk_suites:
            priority_text = "<b>Immediate Attention Required:</b><br/>"
            
            if failed_suites:
                priority_text += f"• <b>Failed Tests</b>: {', '.join(failed_suites)}<br/>"
            
            if high_risk_suites:
                priority_text += f"• <b>High Risk Areas</b>: {', '.join(high_risk_suites)}<br/>"
                
            priority_text += "<br/><b>Focus Areas for Improvement:</b><br/>"
            
            if any('adversarial' in suite.lower() for suite in failed_suites + high_risk_suites):
                priority_text += "• <b>Security Hardening</b>: Strengthen input validation and prompt injection defenses<br/>"
            
            if any('compliance' in suite.lower() or 'ethics' in suite.lower() for suite in failed_suites + high_risk_suites):
                priority_text += "• <b>Compliance Enhancement</b>: Review and update ethical guidelines and bias mitigation<br/>"
            
            if any('explainability' in suite.lower() for suite in failed_suites + high_risk_suites):
                priority_text += "• <b>Transparency Improvement</b>: Enhance reasoning clarity and decision explanation<br/>"
        else:
            priority_text = "<b>✅ All critical areas performing well.</b><br/>Continue with routine monitoring and periodic re-assessment."
        
        story.append(Paragraph(priority_text, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # 监控建议
        story.append(Paragraph("📊 Ongoing Monitoring Recommendations", self.styles['SectionTitle']))
        monitoring_text = """
        <b>Continuous Safety Monitoring:</b><br/>
        • Implement real-time safety scoring for production queries<br/>
        • Set up automated alerts for safety threshold violations<br/>
        • Log all safety-related incidents for pattern analysis<br/>
        • Conduct monthly safety assessments with updated test cases<br/>
        • Monitor for emerging threats and attack vectors<br/><br/>
        <b>Periodic Re-assessment Schedule:</b><br/>
        • Full safety audit: Quarterly<br/>
        • Targeted vulnerability testing: Monthly<br/>
        • Compliance review: Bi-annually<br/>
        • Emergency assessment: After any significant model updates
        """
        story.append(Paragraph(monitoring_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # 报告元信息
        story.append(Paragraph("📄 Report Information", self.styles['SectionTitle']))
        meta_info = f"""
        <b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>AI Safety Lab Version:</b> 1.0.0<br/>
        <b>Test Framework:</b> Comprehensive AI Safety Assessment<br/>
        <b>Report ID:</b> {test_data.get('runId', 'N/A')}<br/><br/>
        <i>This report was automatically generated by AI Safety Lab. For questions about test methodologies or results interpretation, please refer to the documentation or contact the development team.</i>
        """
        story.append(Paragraph(meta_info, self.styles['Normal']))
        
        return story

    def get_filename(self, test_data):
        """Generate a suitable filename for the PDF report"""
        agent = test_data.get('agent', 'Unknown').replace(' ', '_')
        test_type = test_data.get('test_type', 'Test').replace(' ', '_')
        timestamp = test_data.get('timestamp', datetime.now().strftime('%Y-%m-%d_%H-%M-%S')).replace(':', '-').replace(' ', '_')
        
        return f"AI_Safety_Report_{agent}_{test_type}_{timestamp}.pdf"