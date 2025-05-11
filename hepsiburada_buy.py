#!/usr/bin/env python3
"""
hepsiburada_buy.py - HepsiBurada'da ürün sayfasını açıp sepete ekleyen modül (debug özellikli)
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import logging

# Loglamayı ayarla
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def open_url_with_webdriver(url, wait_time=30):
    """
    Verilen URL'yi açar ve ürünü sepete ekler
    
    Args:
        url (str): Açılacak ürün URL'si
        wait_time (int): Elementlerin yüklenmesi için maksimum bekleme süresi (saniye)
    
    Returns:
        webdriver: WebDriver nesnesi
    """
    # Chrome ayarlarını yapılandırma
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    
    # WebDriver servisini başlat
    service = Service("./chromedriver")
    
    logger.info(f"Açılıyor: {url}")
    # WebDriver'ı başlat ve URL'yi aç
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    
    # Sayfanın tamamen yüklenmesini bekle (extra önlem)
    logger.info("Sayfa yüklenmesi bekleniyor...")
    time.sleep(5)  # Hard wait to ensure page loads
    
    # Önce sayfanın HTML içeriğini kontrol edelim
    page_source = driver.page_source
    logger.info(f"Sayfa yüklendi. HTML uzunluğu: {len(page_source)} karakter")
    
    # Sepete ekle butonunu bulmak için tüm potansiyel yöntemleri deneyeceğiz
    button_found = False
    
    try:
        # 1. Yöntem: Orijinal XPath ile deneme
        xpath_to_try = '//*[@id="container"]/div/main/div/div/div[2]/section[1]/div[2]/div[6]/button'
        logger.info(f"XPath deneniyor: {xpath_to_try}")
        
        # Butonun varlığını kontrol et
        add_to_cart_elements = driver.find_elements(By.XPATH, xpath_to_try)
        if add_to_cart_elements:
            logger.info(f"Buton bulundu! İçeriği: {add_to_cart_elements[0].text}")
            try:
                # Butonun görünür ve tıklanabilir olmasını bekle
                wait = WebDriverWait(driver, wait_time)
                add_to_cart_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath_to_try))
                )
                logger.info("Buton tıklanabilir durumda!")
                add_to_cart_button.click()
                logger.info("Buton tıklandı (normal yöntemle)!")
                button_found = True
                time.sleep(2)
            except ElementClickInterceptedException:
                logger.warning("Buton tıklanamadı (engellenmiş). JavaScript ile tıklama deneniyor...")
                # JavaScript ile tıkla
                driver.execute_script("arguments[0].click();", add_to_cart_elements[0])
                logger.info("Buton JavaScript ile tıklandı!")
                button_found = True
                time.sleep(2)
        else:
            logger.warning(f"XPath ile buton bulunamadı: {xpath_to_try}")
    
    except Exception as e:
        logger.error(f"Orijinal XPath ile hata: {str(e)}")
    
    # Eğer hala buton bulunamadıysa daha genel yöntemler deneyelim
    if not button_found:
        logger.info("Alternatif yöntemler deneniyor...")
        
        # 2. Yöntem: Tüm butonları bul ve sepete ekle içerenleri kontrol et
        try:
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"Sayfada toplam {len(all_buttons)} buton bulundu")
            
            for i, button in enumerate(all_buttons):
                try:
                    button_text = button.text.strip()
                    button_class = button.get_attribute("class")
                    button_id = button.get_attribute("id")
                    logger.info(f"Buton {i+1}: Text='{button_text}', Class='{button_class}', ID='{button_id}'")
                    
                    # Sepete ekle butonunu bulmaya çalış
                    if (
                        "sepete ekle" in button_text.lower() or 
                        "sepet" in button_text.lower() or
                        "ekle" in button_text.lower() or
                        "add to cart" in button_text.lower() or
                        "add-to-cart" in button_class.lower() or
                        "addtocart" in button_id.lower()
                    ):
                        logger.info(f"Potansiyel sepete ekle butonu bulundu: {button_text}")
                        try:
                            # Scroll to element
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(1)
                            # Try to click
                            button.click()
                            logger.info(f"Buton {i+1} tıklandı!")
                            button_found = True
                            time.sleep(2)
                            break
                        except ElementClickInterceptedException:
                            # Try JavaScript click
                            driver.execute_script("arguments[0].click();", button)
                            logger.info(f"Buton {i+1} JavaScript ile tıklandı!")
                            button_found = True
                            time.sleep(2)
                            break
                except Exception as e:
                    logger.warning(f"Buton {i+1} için hata: {str(e)}")
        
        except Exception as e:
            logger.error(f"Alternatif buton bulma yönteminde hata: {str(e)}")
    
    # 3. Yöntem: HepsiBurada'nın spesifik dinamik buton yapısına göre deneme
    if not button_found:
        try:
            logger.info("HepsiBurada spesifik yapısına göre deneniyor...")
            potential_xpaths = [
                "//button[contains(., 'Sepete Ekle')]",
                "//button[contains(@class, 'button') and contains(., 'epet')]",
                "//div[contains(@class, 'button-container')]//button",
                "//div[contains(@class, 'add-to-cart')]//button",
                "//*[contains(@id, 'addToCart')]",
                "//*[contains(@id, 'add-to-cart')]",
                "//button[contains(@data-test-id, 'add-to-cart')]",
                "//button[contains(@data-test-id, 'addToCart')]"
            ]
            
            for xpath in potential_xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    if elements:
                        logger.info(f"Bulunan eleman sayısı ({xpath}): {len(elements)}")
                        for i, elem in enumerate(elements):
                            logger.info(f"Eleman {i+1} metni: '{elem.text}'")
                            try:
                                # Görünür olmasını sağla
                                driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                                time.sleep(1)
                                # Tıkla
                                elem.click()
                                logger.info(f"XPath {xpath} ile buton tıklandı!")
                                button_found = True
                                time.sleep(2)
                                break
                            except ElementClickInterceptedException:
                                # JavaScript ile tıkla
                                driver.execute_script("arguments[0].click();", elem)
                                logger.info(f"XPath {xpath} ile buton JavaScript ile tıklandı!")
                                button_found = True
                                time.sleep(2)
                                break
                    if button_found:
                        break
                except Exception as e:
                    logger.warning(f"XPath {xpath} için hata: {str(e)}")
        
        except Exception as e:
            logger.error(f"HepsiBurada spesifik yönteminde hata: {str(e)}")
    
    # 4. Yöntem: Sayfa yapısını tamamen analiz et
    if not button_found:
        logger.info("Son çare: Sayfa yapısını analiz ediyorum...")
        
        # Sayfa yapısı hakkında daha fazla bilgi topla
        try:
            # Sayfadaki tüm linkleri kontrol et (bazen sepete ekle link olabilir)
            links = driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Sayfada {len(links)} link bulundu")
            
            for i, link in enumerate(links):
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href")
                    
                    if (
                        "sepete ekle" in link_text.lower() or 
                        "sepet" in link_text.lower() or
                        "cart" in link_href.lower()
                    ):
                        logger.info(f"Potansiyel sepet linki bulundu: {link_text}")
                        try:
                            link.click()
                            logger.info("Link tıklandı!")
                            button_found = True
                            time.sleep(2)
                            break
                        except:
                            driver.execute_script("arguments[0].click();", link)
                            logger.info("Link JavaScript ile tıklandı!")
                            button_found = True
                            time.sleep(2)
                            break
                except:
                    pass
        except Exception as e:
            logger.error(f"Link analizinde hata: {str(e)}")
    
    # Sonucu raporla
    if button_found:
        logger.info("İşlem başarılı: Ürün sepete eklendi (veya buton tıklandı)")
    else:
        logger.error("İşlem başarısız: Sepete ekle butonu bulunamadı veya tıklanamadı")
        
        # Son çare olarak ürün detaylarını alalım (hata ayıklama için)
        try:
            logger.info("Ürün detayları alınıyor...")
            product_title_elements = driver.find_elements(By.TAG_NAME, "h1")
            if product_title_elements:
                logger.info(f"Ürün başlığı: {product_title_elements[0].text}")
            
            # XPath ile sayfanın yapısını kontrol et
            main_container = driver.find_elements(By.XPATH, '//*[@id="container"]')
            if main_container:
                logger.info("Ana konteyner (#container) bulundu")
                
                # Div yapısını kontrol et
                div_structure = driver.find_elements(By.XPATH, '//*[@id="container"]/div/main')
                if div_structure:
                    logger.info("Div yapısı doğrulanıyor...")
                    # Orijinal XPath'in her kısmını kontrol et
                    for i in range(2, 7):
                        xpath_part = f'//*[@id="container"]/div/main/div/div/div[2]/section[1]/div[2]/div[{i}]'
                        elements = driver.find_elements(By.XPATH, xpath_part)
                        logger.info(f"XPath parçası {xpath_part}: {len(elements)} eleman bulundu")
        except Exception as e:
            logger.error(f"Ürün detayları alınırken hata: {str(e)}")
    
    return driver

# Komut satırından da çalıştırılabilir olması için
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Kullanım: python hepsiburada_buy.py <ürün_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    try:
        # URL'yi aç ve sepete ekle
        driver = open_url_with_webdriver(url)
        
        input("Tarayıcıyı kapatmak için Enter tuşuna basın...")
        driver.quit()
    except Exception as e:
        logger.error(f"Ana program hatası: {e}")
        sys.exit(1)