import io
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple
from app.config import MAX_IMAGE_SIZE_MB, MAX_URL_FETCH_TIMEOUT_SEC

class URLFetcher:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 LegalMetrologyChecker/1.0"

    @classmethod
    def fetch_image_from_url(cls, url: str) -> Dict[str, Any]:
        """
        Safely fetches image from direct image URL or extracts top product image from a product page.
        Returns:
            - success: bool
            - images: List[np.ndarray (BGR)]
            - source_urls: List[str]
            - error: Optional[str]
        """
        if not url or not url.strip():
            return {"success": False, "images": [], "error": "URL cannot be empty."}

        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        try:
            parsed = urllib.parse.urlparse(target_url)
            if not parsed.netloc:
                return {"success": False, "images": [], "error": "Invalid URL domain format."}
        except Exception as e:
            return {"success": False, "images": [], "error": f"Invalid URL: {str(e)}"}

        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            # Stream first few bytes to check Content-Type and size
            with requests.get(target_url, headers=headers, timeout=MAX_URL_FETCH_TIMEOUT_SEC, stream=True) as resp:
                if resp.status_code == 403:
                    return {
                        "success": False,
                        "images": [],
                        "error": "Access Forbidden (403): The target server blocked the request. Try downloading and uploading the image directly."
                    }
                elif resp.status_code == 404:
                    return {"success": False, "images": [], "error": "Target URL returned 404 Not Found."}
                elif resp.status_code >= 400:
                    return {"success": False, "images": [], "error": f"Target server returned HTTP {resp.status_code}."}

                content_type = resp.headers.get("Content-Type", "").lower()
                
                # Case 1: Direct Image Content
                if "image" in content_type:
                    image_bytes = resp.content
                    if len(image_bytes) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                        return {"success": False, "images": [], "error": f"Image exceeds maximum size limit ({MAX_IMAGE_SIZE_MB}MB)."}

                    cv_img = cls._bytes_to_cv2(image_bytes)
                    if cv_img is None:
                        return {"success": False, "images": [], "error": "Fetched data could not be decoded as a valid image format."}
                    
                    return {
                        "success": True,
                        "images": [cv_img],
                        "source_urls": [target_url],
                        "page_title": "Direct Image URL",
                        "error": None
                    }

                # Case 2: HTML Page (Product Listing / Web page)
                elif "html" in content_type or "text" in content_type:
                    html_text = resp.text
                    extracted_images, candidate_urls, page_title = cls._extract_images_from_html(html_text, target_url, headers)
                    
                    if not extracted_images:
                        return {
                            "success": False,
                            "images": [],
                            "error": "The URL is an HTML webpage, but no valid product packaging images could be found or fetched from it."
                        }

                    return {
                        "success": True,
                        "images": extracted_images,
                        "source_urls": candidate_urls,
                        "page_title": page_title,
                        "error": None
                    }
                
                else:
                    return {
                        "success": False,
                        "images": [],
                        "error": f"Unsupported Content-Type '{content_type}'. Please provide a direct image URL or product page URL."
                    }

        except requests.exceptions.Timeout:
            return {"success": False, "images": [], "error": f"URL request timed out after {MAX_URL_FETCH_TIMEOUT_SEC} seconds."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "images": [], "error": "Connection failed. Please verify the URL domain."}
        except Exception as e:
            return {"success": False, "images": [], "error": f"Error fetching URL: {str(e)}"}

    @classmethod
    def _extract_images_from_html(cls, html_text: str, base_url: str, headers: dict) -> Tuple[List[np.ndarray], List[str], str]:
        soup = BeautifulSoup(html_text, "html.parser")
        page_title = soup.title.string.strip() if soup.title and soup.title.string else "Product Webpage"

        candidate_urls: List[str] = []

        # 1. Check OpenGraph / Twitter metadata
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og_img and og_img.get("content"):
            candidate_urls.append(og_img["content"].strip())

        tw_img = soup.find("meta", attrs={"name": "twitter:image"}) or soup.find("meta", property="twitter:image")
        if tw_img and tw_img.get("content"):
            candidate_urls.append(tw_img["content"].strip())

        # 2. Check JSON-LD schema
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string and ("image" in script.string or "Product" in script.string):
                found_imgs = re.findall(r'"image":\s*(?:"([^"]+)"|\[([^\]]+)\])', script.string)
                for f_img in found_imgs:
                    for item in f_img:
                        if item:
                            clean_items = re.findall(r'https?://[^\s",]+', item)
                            candidate_urls.extend(clean_items)

        # 3. Check regular <img> tags with product-like classes/attributes
        for img_tag in soup.find_all("img"):
            src = img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("src")
            if src and not src.startswith("data:image"):
                # Prioritize large product images, ignore tiny icons/sprites
                if any(k in (img_tag.get("class", []) if isinstance(img_tag.get("class"), list) else [str(img_tag.get("class", ""))]) for k in ["product", "main", "gallery", "zoom", "featured", "detail", "landing"]):
                    candidate_urls.append(src)
                elif any(k in src.lower() for k in ["product", "item", "zoom", "large", "image", "upload", "sku"]):
                    candidate_urls.append(src)

        # Resolve relative URLs & deduplicate
        resolved_urls = []
        for u in candidate_urls:
            full_u = urllib.parse.urljoin(base_url, u)
            if full_u not in resolved_urls and not full_u.endswith((".svg", ".gif", ".ico")):
                resolved_urls.append(full_u)

        # Download up to 3 highest-priority product images
        valid_images = []
        fetched_urls = []

        for candidate in resolved_urls[:4]:
            try:
                res = requests.get(candidate, headers=headers, timeout=8)
                if res.status_code == 200 and "image" in res.headers.get("Content-Type", "").lower():
                    cv_img = cls._bytes_to_cv2(res.content)
                    if cv_img is not None:
                        h, w = cv_img.shape[:2]
                        # Filter out tiny tracking pixels or icons (< 150px)
                        if h >= 150 and w >= 150:
                            valid_images.append(cv_img)
                            fetched_urls.append(candidate)
                            if len(valid_images) >= 3:
                                break
            except Exception:
                continue

        return valid_images, fetched_urls, page_title

    @staticmethod
    def _bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
        try:
            # Check with PIL to verify integrity
            pil_img = Image.open(io.BytesIO(image_bytes))
            pil_img.verify()
            
            # Reopen and convert to RGB
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return cv_img
        except Exception:
            return None
