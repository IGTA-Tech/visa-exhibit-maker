"""
URL to PDF Handler - Convert web pages to PDFs using API2PDF
V2: Added for visa exhibit generation from media articles

API2PDF Documentation: https://www.api2pdf.com/documentation
"""

import os
import requests
import tempfile
from typing import Dict, Optional
from urllib.parse import urlparse


class URLToPDFHandler:
    """Handle URL to PDF conversions using API2PDF"""

    def __init__(self, api_key: str):
        """
        Initialize handler with API2PDF key

        Args:
            api_key: API2PDF API key
        """
        self.api_key = api_key
        self.base_url = "https://v2.api2pdf.com/chrome/pdf/url"
        self.temp_dir = tempfile.gettempdir()

    def convert_url_to_pdf(
        self,
        url: str,
        filename: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Dict:
        """
        Convert a URL to PDF

        Args:
            url: Web page URL to convert
            filename: Optional output filename
            options: Optional conversion options

        Returns:
            Dict with success status, file path, and metadata
        """
        try:
            # Default options for good quality
            default_options = {
                'url': url,
                'inline': False,
                'options': {
                    'landscape': False,
                    'printBackground': True,
                    'marginTop': 0.5,
                    'marginBottom': 0.5,
                    'marginLeft': 0.5,
                    'marginRight': 0.5
                }
            }

            if options:
                default_options['options'].update(options)

            # Make API request
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }

            response = requests.post(
                self.base_url,
                json=default_options,
                headers=headers,
                timeout=60
            )

            result = response.json()

            if result.get('success'):
                # Download the PDF
                pdf_url = result.get('pdf') or result.get('FileUrl')

                if not filename:
                    # Generate filename from URL
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace('www.', '').replace('.', '_')
                    path_part = parsed.path.replace('/', '_')[:30]
                    filename = f"{domain}{path_part}_article.pdf"
                    # Clean filename
                    filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
                    if not filename.endswith('.pdf'):
                        filename += '.pdf'

                # Download PDF to temp directory
                output_path = os.path.join(self.temp_dir, filename)

                pdf_response = requests.get(pdf_url, timeout=60)
                with open(output_path, 'wb') as f:
                    f.write(pdf_response.content)

                return {
                    'success': True,
                    'url': url,
                    'pdf_path': output_path,
                    'filename': filename,
                    'file_size': os.path.getsize(output_path)
                }

            else:
                return {
                    'success': False,
                    'url': url,
                    'error': result.get('error', 'Unknown error from API2PDF')
                }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'url': url,
                'error': 'Request timed out'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'url': url,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }

    def convert_multiple_urls(
        self,
        urls: list,
        on_progress: callable = None
    ) -> list:
        """
        Convert multiple URLs to PDFs

        Args:
            urls: List of URLs to convert
            on_progress: Optional callback(current, total, url)

        Returns:
            List of conversion results
        """
        results = []

        for i, url in enumerate(urls):
            if on_progress:
                on_progress(i + 1, len(urls), url)

            result = self.convert_url_to_pdf(url)
            results.append(result)

        return results

    def get_api_usage(self) -> Dict:
        """
        Get API usage statistics (if available)

        Returns:
            Dict with usage info
        """
        try:
            # API2PDF doesn't have a direct usage endpoint
            # This is a placeholder for future implementation
            return {
                'success': True,
                'message': 'Usage tracking not available via API'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
