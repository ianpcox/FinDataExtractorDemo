"""PDF preprocessing module for optimization before extraction

Provides optional preprocessing steps to optimize PDFs before sending to Azure Document Intelligence:
- PDF compression (text-based PDFs)
- Image optimization (scanned PDFs - resize, denoise, contrast enhancement)
- Page rotation correction
- DPI normalization

This can reduce costs (smaller files = fewer pages processed) and improve extraction accuracy.
"""

from typing import Optional, Tuple, Dict, Any
from io import BytesIO
import logging

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from src.config import settings

logger = logging.getLogger(__name__)


class PDFPreprocessor:
    """Handles PDF preprocessing and optimization"""
    
    def __init__(
        self,
        enable_compression: Optional[bool] = None,
        enable_image_optimization: Optional[bool] = None,
        target_dpi: Optional[int] = None,
        max_image_dpi: Optional[int] = None,
        enable_rotation_correction: Optional[bool] = None,
    ):
        """
        Initialize PDF preprocessor
        
        Args:
            enable_compression: Enable PDF compression (defaults to settings.ENABLE_PDF_PREPROCESSING)
            enable_image_optimization: Enable image optimization for scanned PDFs
            target_dpi: Target DPI for image optimization (defaults to 300)
            max_image_dpi: Maximum DPI before downscaling (defaults to 600)
            enable_rotation_correction: Enable automatic page rotation correction
        """
        self.enable_compression = (
            enable_compression if enable_compression is not None
            else getattr(settings, "ENABLE_PDF_PREPROCESSING", False)
        )
        self.enable_image_optimization = (
            enable_image_optimization if enable_image_optimization is not None
            else getattr(settings, "ENABLE_PDF_IMAGE_OPTIMIZATION", False)
        )
        self.target_dpi = target_dpi or getattr(settings, "PDF_PREPROCESS_TARGET_DPI", 300)
        self.max_image_dpi = max_image_dpi or getattr(settings, "PDF_PREPROCESS_MAX_DPI", 600)
        self.enable_rotation_correction = (
            enable_rotation_correction if enable_rotation_correction is not None
            else getattr(settings, "ENABLE_PDF_ROTATION_CORRECTION", False)
        )
    
    def preprocess(
        self,
        file_content: bytes,
        file_name: str
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Preprocess PDF to optimize for extraction
        
        Args:
            file_content: Original PDF content as bytes
            file_name: Original file name (for logging)
            
        Returns:
            Tuple of (processed_pdf_bytes, preprocessing_stats)
            
        Preprocessing stats include:
            - original_size: Original file size in bytes
            - processed_size: Processed file size in bytes
            - size_reduction: Percentage reduction
            - preprocessing_applied: List of preprocessing steps applied
            - error: Error message if preprocessing failed (original file returned)
        """
        stats = {
            "original_size": len(file_content),
            "processed_size": len(file_content),
            "size_reduction": 0.0,
            "preprocessing_applied": [],
            "error": None
        }
        
        # If preprocessing is disabled, return original
        if not self.enable_compression and not self.enable_image_optimization and not self.enable_rotation_correction:
            logger.debug("PDF preprocessing disabled, returning original file")
            return file_content, stats
        
        try:
            processed_content = file_content
            original_size = len(file_content)
            
            # Detect PDF type (text-based vs scanned)
            is_scanned = self._is_scanned_pdf(file_content)
            
            logger.info(
                f"Preprocessing PDF: {file_name} "
                f"({original_size} bytes, scanned: {is_scanned})"
            )
            
            # Apply preprocessing based on PDF type
            if is_scanned and self.enable_image_optimization:
                processed_content = self._optimize_scanned_pdf(processed_content, file_name)
                stats["preprocessing_applied"].append("image_optimization")
            
            if self.enable_compression:
                processed_content = self._compress_pdf(processed_content, file_name)
                stats["preprocessing_applied"].append("compression")
            
            if self.enable_rotation_correction:
                processed_content = self._correct_rotation(processed_content, file_name)
                stats["preprocessing_applied"].append("rotation_correction")
            
            # Calculate stats
            processed_size = len(processed_content)
            stats["processed_size"] = processed_size
            if original_size > 0:
                stats["size_reduction"] = ((original_size - processed_size) / original_size) * 100
            
            if stats["preprocessing_applied"]:
                logger.info(
                    f"PDF preprocessing completed: {file_name} "
                    f"({original_size} -> {processed_size} bytes, "
                    f"{stats['size_reduction']:.1f}% reduction, "
                    f"steps: {', '.join(stats['preprocessing_applied'])})"
                )
            
            return processed_content, stats
            
        except Exception as e:
            logger.warning(f"PDF preprocessing failed for {file_name}, using original: {e}", exc_info=True)
            stats["error"] = str(e)
            return file_content, stats
    
    def _is_scanned_pdf(self, file_content: bytes) -> bool:
        """
        Detect if PDF is primarily scanned/images (vs text-based)
        
        Returns:
            True if PDF appears to be scanned/image-based
        """
        if not PYPDF2_AVAILABLE:
            return False
        
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Check first page for text content
            if len(pdf_reader.pages) == 0:
                return False
            
            first_page = pdf_reader.pages[0]
            text = first_page.extract_text()
            
            # If very little text extracted, likely scanned
            if text is None or len(text.strip()) < 50:
                return True
            
            return False
            
        except Exception:
            logger.debug("Could not determine if PDF is scanned, assuming text-based")
            return False
    
    def _compress_pdf(self, file_content: bytes, file_name: str) -> bytes:
        """
        Compress PDF file
        
        Args:
            file_content: PDF content as bytes
            file_name: File name for logging
            
        Returns:
            Compressed PDF as bytes
        """
        if not PYPDF2_AVAILABLE:
            logger.warning("PyPDF2 not available, skipping compression")
            return file_content
        
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_writer = PyPDF2.PdfWriter()
            
            # Copy pages with compression
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            
            # Write compressed PDF
            output = BytesIO()
            pdf_writer.write(output)
            compressed = output.getvalue()
            
            logger.debug(f"PDF compression: {file_name} ({len(file_content)} -> {len(compressed)} bytes)")
            return compressed
            
        except Exception as e:
            logger.warning(f"PDF compression failed for {file_name}: {e}")
            return file_content
    
    def _optimize_scanned_pdf(self, file_content: bytes, file_name: str) -> bytes:
        """
        Optimize scanned PDF images (resize, denoise, enhance contrast)
        
        Args:
            file_content: PDF content as bytes
            file_name: File name for logging
            
        Returns:
            Optimized PDF as bytes
        """
        if not PYMUPDF_AVAILABLE or not PILLOW_AVAILABLE:
            logger.warning("PyMuPDF or Pillow not available, skipping image optimization")
            return file_content
        
        try:
            # Open PDF with PyMuPDF
            pdf_doc = fitz.open(stream=file_content, filetype="pdf")
            output_pdf = fitz.open()
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Get page as image
                zoom = self.target_dpi / 72.0  # PyMuPDF uses 72 DPI as base
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(BytesIO(img_data))
                
                # Check if we need to downscale
                current_dpi = pix.xres if hasattr(pix, 'xres') else self.target_dpi
                if current_dpi > self.max_image_dpi:
                    # Calculate scale factor
                    scale_factor = self.max_image_dpi / current_dpi
                    new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.debug(f"Downscaled page {page_num + 1} from {current_dpi} DPI to ~{self.max_image_dpi} DPI")
                
                # Convert to grayscale if color not needed (smaller file size)
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Enhance contrast slightly (helps OCR)
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.1)  # 10% contrast increase
                
                # Apply gentle denoising
                img = img.filter(ImageFilter.MedianFilter(size=3))
                
                # Convert back to PDF page
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG', optimize=True)
                img_bytes.seek(0)
                
                # Insert optimized image as new page
                img_rect = fitz.Rect(0, 0, img.width, img.height)
                new_page = output_pdf.new_page(width=img.width, height=img.height)
                new_page.insert_image(img_rect, stream=img_bytes.getvalue())
            
            # Get optimized PDF bytes
            output_bytes = output_pdf.tobytes()
            output_pdf.close()
            pdf_doc.close()
            
            logger.debug(f"Image optimization: {file_name} ({len(file_content)} -> {len(output_bytes)} bytes)")
            return output_bytes
            
        except Exception as e:
            logger.warning(f"Image optimization failed for {file_name}: {e}", exc_info=True)
            return file_content
    
    def _correct_rotation(self, file_content: bytes, file_name: str) -> bytes:
        """
        Correct page rotation (auto-rotate pages to correct orientation)
        
        Args:
            file_content: PDF content as bytes
            file_name: File name for logging
            
        Returns:
            PDF with corrected rotation as bytes
        """
        if not PYPDF2_AVAILABLE:
            logger.warning("PyPDF2 not available, skipping rotation correction")
            return file_content
        
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_writer = PyPDF2.PdfWriter()
            
            rotation_corrected = False
            for page in pdf_reader.pages:
                # Get rotation from page
                rotation = page.get('/Rotate', 0)
                
                # If page is rotated 90 or 270 degrees, correct it
                if rotation in [90, 270]:
                    page.rotate(-rotation)
                    rotation_corrected = True
                
                pdf_writer.add_page(page)
            
            if rotation_corrected:
                output = BytesIO()
                pdf_writer.write(output)
                corrected = output.getvalue()
                logger.debug(f"Rotation correction applied to {file_name}")
                return corrected
            
            return file_content
            
        except Exception as e:
            logger.warning(f"Rotation correction failed for {file_name}: {e}")
            return file_content

