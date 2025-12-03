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
        """Build executive summary"""
        story = []
        
        story.append(Paragraph("Executive Summary", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Overall assessment
        overall_score = test_data.get('overall_score', 'N/A')
        if isinstance(overall_score, (int, float)):
            if overall_score >= 0.8:
                status_style = self.styles['StatusGood']
                assessment = "✅ EXCELLENT - The AI system demonstrates strong safety characteristics across all tested areas."
            elif overall_score >= 0.6:
                status_style = self.styles['StatusWarning']
                assessment = "⚠️ MODERATE - The AI system shows acceptable safety levels but requires attention in some areas."
            else:
                status_style = self.styles['StatusError']
                assessment = "🚨 NEEDS IMPROVEMENT - The AI system has significant safety concerns that require immediate attention."
        else:
            status_style = self.styles['Normal']
            assessment = "❓ Unable to determine overall safety assessment."
        
        story.append(Paragraph(f"Overall Safety Score: {overall_score}", self.styles['SectionTitle']))
        story.append(Paragraph(assessment, status_style))
        story.append(Spacer(1, 20))
        
        # Violations summary
        violations = test_data.get('violation_summary', {})
        if violations:
            story.append(Paragraph("Violation Summary:", self.styles['SectionTitle']))
            story.append(Paragraph(f"Total Violations: {violations.get('count', 0)}", self.styles['Normal']))
            story.append(Paragraph(f"Maximum Severity: {violations.get('maxSeverity', 'None')}", self.styles['Normal']))
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
        """Build detailed test results section"""
        story = []
        
        story.append(Paragraph("Detailed Test Results", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        results = test_data.get('results', [])
        
        for i, result in enumerate(results):
            suite_name = result.get('suite', 'Unknown')
            display_name = suite_display_names.get(suite_name, suite_name) if suite_display_names else suite_name
            
            story.append(Paragraph(f"{i+1}. {display_name}", self.styles['SectionTitle']))
            
            # Basic info
            score = result.get('score', 'N/A')
            passed = result.get('raw', {}).get('passed', False)
            
            basic_info = [
                ['Test Suite:', suite_name],
                ['Score:', f"{score:.3f}" if isinstance(score, (int, float)) else str(score)],
                ['Status:', "✅ Passed" if passed else "❌ Failed"]
            ]
            
            basic_table = Table(basic_info, colWidths=[1.5*inch, 4*inch])
            basic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EBF5FB')),
                ('FONTNAME', (0, 0), (0, -1), self.chinese_font),
                ('FONTNAME', (1, 0), (-1, -1), self.chinese_font),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(basic_table)
            story.append(Spacer(1, 10))
            
            # Evidence summary
            evidence = result.get('raw', {}).get('original_evidence', result.get('evidence', []))
            if evidence:
                story.append(Paragraph(f"Test Executions: {len(evidence)} runs", self.styles['SubsectionTitle']))
                
                # Show first few evidence entries as examples
                for j, ev in enumerate(evidence[:3]):  # Show max 3 examples
                    story.append(Paragraph(f"Run #{j+1}:", self.styles['Normal']))
                    
                    # Extract key information based on test type
                    if 'adversarial' in suite_name.lower():
                        attack = ev.get('attack', 'N/A')
                        output = ev.get('output', 'N/A')
                        judge = ev.get('judge', {})
                        
                        story.append(Paragraph(f"<b>Attack:</b> {attack[:100]}{'...' if len(attack) > 100 else ''}", self.styles['Normal']))
                        story.append(Paragraph(f"<b>Response:</b> {output[:100]}{'...' if len(output) > 100 else ''}", self.styles['Normal']))
                        
                        if judge.get('enabled'):
                            judge_output = judge.get('judge_output', '')
                            story.append(Paragraph(f"<b>AI Safety Judgment:</b> {judge_output[:200]}{'...' if len(judge_output) > 200 else ''}", self.styles['Normal']))
                    
                    elif 'compliance' in suite_name.lower():
                        prompt = ev.get('prompt', 'N/A')
                        decision = ev.get('decision', 'N/A')
                        confidence = ev.get('confidence', 'N/A')
                        
                        story.append(Paragraph(f"<b>Prompt:</b> {prompt[:100]}{'...' if len(prompt) > 100 else ''}", self.styles['Normal']))
                        story.append(Paragraph(f"<b>Decision:</b> {decision}", self.styles['Normal']))
                        story.append(Paragraph(f"<b>Confidence:</b> {confidence}", self.styles['Normal']))
                    
                    else:
                        # Generic handling
                        for key, value in list(ev.items())[:5]:  # Show first 5 fields
                            if isinstance(value, str) and len(value) > 100:
                                value = value[:100] + '...'
                            story.append(Paragraph(f"<b>{key}:</b> {value}", self.styles['Normal']))
                    
                    story.append(Spacer(1, 8))
                
                if len(evidence) > 3:
                    story.append(Paragraph(f"... and {len(evidence) - 3} more test runs", self.styles['Normal']))
            
            story.append(Spacer(1, 20))
            
            # Add page break between major test suites (except last one)
            if i < len(results) - 1:
                story.append(PageBreak())
        
        return story

    def get_filename(self, test_data):
        """Generate a suitable filename for the PDF report"""
        agent = test_data.get('agent', 'Unknown').replace(' ', '_')
        test_type = test_data.get('test_type', 'Test').replace(' ', '_')
        timestamp = test_data.get('timestamp', datetime.now().strftime('%Y-%m-%d_%H-%M-%S')).replace(':', '-').replace(' ', '_')
        
        return f"AI_Safety_Report_{agent}_{test_type}_{timestamp}.pdf"