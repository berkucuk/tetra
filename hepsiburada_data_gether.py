from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import sys
import json
import re
import random
from selenium.common.exceptions import TimeoutException

def hepsiburada_urunleri_incele(arama_kelimesi, urun_sayisi=10):
    # JSON verisini tutacak dictionary
    urun_verileri = {}
    
    # Chrome ayarlarını yapılandırma
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Yeni ve daha iyi headless mod
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920x1080")  # Tam ekran boyutu
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Bot tespitini önlemek için daha fazla seçenek
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    
    # Rastgele user-agent ekle - gerçek bir tarayıcı gibi görün
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    # Driver yolu
    driver_path = "./chromedriver"
        
    if not os.path.exists(driver_path) and driver_path != "chromedriver":
        print(f"UYARI: {driver_path} bulunamadı. PATH'te olduğundan emin olun veya doğru yolu belirtin.")
        driver_path = "chromedriver"
    
    service = Service(driver_path)
    
    try:
        # WebDriver'ı başlat
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # WebDriver javascript değişkenini gizle
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });
            
            // Selenium tanımlamalarını gizle
            window.navigator.chrome = {
                runtime: {},
            };
            
            // Ek Javascript gizleme
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'tr']
            });
            """
        })

        # Hepsiburada ana sayfasına git ve arama yap
        print("Hepsiburada sitesine bağlanılıyor...")
        driver.get(f"https://www.hepsiburada.com/ara?q={arama_kelimesi}")
        print(f"Hepsiburada sitesi açıldı ve '{arama_kelimesi}' için arama yapıldı.")
        
        # Cookie/popup kapatma - bunlar veri çekmeyi engelleyebilir
        try:
            # Çerezleri kabul et butonu varsa tıkla
            cookie_buttons = [
                "//button[contains(@id, 'onetrust-accept')]",
                "//button[contains(text(), 'Kabul')]", 
                "//button[contains(text(), 'Tümünü Kabul Et')]",
                "//div[contains(@class, 'closeIcon')]"
            ]
            
            for button_xpath in cookie_buttons:
                try:
                    cookie_button = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, button_xpath))
                    )
                    cookie_button.click()
                    print("Cookie mesajı kapatıldı.")
                    time.sleep(1)
                    break
                except:
                    continue
        except:
            pass
        
        # Sayfanın yüklenmesi için bekle
        time.sleep(3)
        
        # Kaç ürün incelenecek
        incelenecek_urun_sayisi = min(urun_sayisi, 5)  # En fazla 10 ürün
        print(f"İlk {incelenecek_urun_sayisi} ürün incelenecek.")
        
        # Her bir ürünü incele
        for i in range(incelenecek_urun_sayisi):
            try:
                # Ürün kartı XPath'i - ORIJINAL
                urun_karti_xpath = f"//*[@id='i{i}']/article/a"
                
                print(f"\n{i+1}. ürüne geçiliyor...")
                
                # Ürün kartını bul
                try:
                    # Ürün kartını daha güvenilir şekilde bul - birkaç deneme yap
                    max_retries = 3
                    urun_karti = None
                    
                    for _ in range(max_retries):
                        try:
                            # Ürün kartını bekleme süresiyle aramayı dene
                            urun_karti = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, urun_karti_xpath))
                            )
                            if urun_karti:
                                break
                        except:
                            # Sayfayı biraz aşağı kaydır ve tekrar dene
                            driver.execute_script("window.scrollBy(0, 300);")
                            time.sleep(1)
                    
                    if not urun_karti:
                        print(f"Ürün kartı bulunamadı, sonraki ürüne geçiliyor.")
                        continue
                    
                    # Ürün kartına scroll yap
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", urun_karti)
                    time.sleep(1)
                    
                    # Ürün json verisi
                    urun_data = {
                        "urun_adi": "",
                        "urun_link": "",
                        "fiyat": "",
                        "marka": ""
                    }
                    
                    # Ürün linkini al
                    try:
                        urun_link = urun_karti.get_attribute("href")
                        if urun_link:
                            print(f"Ürün linki: {urun_link}")
                            urun_data["urun_link"] = urun_link
                    except Exception as e:
                        print(f"Ürün linki alınamadı: {str(e)}")
                    
                    # ÜRÜN ADI ALMA - ORIJINAL XPATH'LER
                    # Birden fazla strateji ile ürün adını almaya çalışıyoruz
                    
                    # Strateji 1: Farklı olası ürün adı XPath'lerini deneme
                    urun_adi_bulundu = False
                    
                    # Ürün adı için olası XPath'ler
                    urun_adi_xpath_listesi = [
                        # Ürün başlık XPath'leri (product-title-x-y formatı)
                        f"//*[@id='product-title-{i+1}-{i+1}']/span",
                        f"//*[@id='product-title-1-{i+1}']/span",
                        f"//*[@id='product-title-{i+1}']/span",
                        
                        # Tüm "ürün adı" olabilecek XPath'leri dene (sayfa başındaki değil, ürün kartındaki)
                        f"//*[@id='i{i}']//h3",
                        f"//*[@id='i{i}']//div[contains(@class, 'name')]",
                        f"//*[@id='i{i}']//div[contains(@class, 'title')]",
                        f"//*[@id='i{i}']//a[contains(@title, '')]"
                    ]
                    
                    for urun_adi_xpath in urun_adi_xpath_listesi:
                        if urun_adi_bulundu:
                            break
                            
                        try:
                            urun_adi_elementi = WebDriverWait(driver, 2).until(
                                EC.presence_of_element_located((By.XPATH, urun_adi_xpath))
                            )
                            urun_adi = urun_adi_elementi.text
                            
                            # Text boşsa ve title özelliği varsa, title'dan alalım
                            if not urun_adi:
                                urun_adi = urun_adi_elementi.get_attribute("title")
                            
                            if urun_adi:
                                print(f"Ürün adı: {urun_adi} (XPath: {urun_adi_xpath})")
                                urun_data["urun_adi"] = urun_adi
                                urun_adi_bulundu = True
                                break
                        except:
                            continue
                    
                    # Strateji 2: Ürün kartı içindeki öğeleri direkt kontrol et
                    if not urun_adi_bulundu:
                        try:
                            # Önce h3 etiketlerini ara
                            h3_elements = urun_karti.find_elements(By.TAG_NAME, "h3")
                            for element in h3_elements:
                                urun_adi = element.text
                                if urun_adi:
                                    print(f"Ürün adı (h3): {urun_adi}")
                                    urun_data["urun_adi"] = urun_adi
                                    urun_adi_bulundu = True
                                    break
                            
                            # h3 bulunamadıysa, title özelliği olan tüm öğeleri ara
                            if not urun_adi_bulundu:
                                title_elements = urun_karti.find_elements(By.XPATH, ".//*[@title]")
                                for element in title_elements:
                                    urun_adi = element.get_attribute("title")
                                    if urun_adi:
                                        print(f"Ürün adı (title): {urun_adi}")
                                        urun_data["urun_adi"] = urun_adi
                                        urun_adi_bulundu = True
                                        break
                        except Exception as e:
                            print(f"Alternatif ürün adı alma yönteminde hata: {str(e)}")
                    
                    # Strateji 3: Eğer link var ve ürün adı yoksa, linkten çıkarmayı dene
                    if not urun_adi_bulundu and urun_link:
                        try:
                            # Ürün linkinden ürün adını çıkarmaya çalış
                            # Örnek link: https://www.hepsiburada.com/hp-250-g10-intel-core-i5-1334u-16gb-512gb-ssd...
                            path_parts = urun_link.split('/')
                            if len(path_parts) > 4:  # www.hepsiburada.com/urun-adi-pm-... formatı
                                urun_yolu = path_parts[4].split('-pm-')[0]
                                urun_adi = urun_yolu.replace('-', ' ').title()
                                print(f"Link'ten çıkarılan ürün adı: {urun_adi}")
                                urun_data["urun_adi"] = urun_adi
                                urun_adi_bulundu = True
                        except Exception as e:
                            print(f"Link'ten ürün adı çıkarma hatası: {str(e)}")
                    
                    # FİYAT BİLGİSİNİ ALMA - ORIJINAL XPATH'LER
                    # Fiyat XPath'lerinin farklılığı nedeniyle birden çok strateji deniyoruz
                    
                    # Strateji 1: Doğrudan fiyat XPath'leri - farklı yapıları dene
                    fiyat_bulundu = False
                    
                    # Olası fiyat XPath şablonları
                    fiyat_xpath_sablonlari = [
                        # Yaygın fiyat XPath'leri
                        f"//*[@id='i{i}']/article/a/div/div[3]/div/div",
                        f"//*[@id='i{i}']/article/a/div/div[4]/div/div",
                        f"//*[@id='i{i}']/article/a/div/div[3]/div/div[2]",
                        f"//*[@id='i{i}']/article/a/div/div[4]/div/div[2]",
                        
                        # Fiyat sınıfı içeren XPath'ler
                        f"//*[@id='i{i}']//div[contains(@data-test-id, 'price')]",
                        f"//*[@id='i{i}']//div[contains(@class, 'price')]"
                    ]
                    
                    for fiyat_xpath in fiyat_xpath_sablonlari:
                        if fiyat_bulundu:
                            break
                            
                        try:
                            fiyat_elementi = WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.XPATH, fiyat_xpath))
                            )
                            fiyat_text = fiyat_elementi.text
                            
                            # Fiyat metnini doğrula - TL içermeli veya rakam içermeli
                            if fiyat_text and ("TL" in fiyat_text or any(c.isdigit() for c in fiyat_text)):
                                # Ürün puanı değil, gerçek fiyat olup olmadığını kontrol et
                                if not ("Ürün puanı" in fiyat_text or "değerlendirme" in fiyat_text):
                                    # Fiyat formatını temizle (% işaretini ve sonrasını kaldır)
                                    fiyat_text = re.sub(r'%.*$', '', fiyat_text).strip()
                                    
                                    print(f"Ürün fiyatı: {fiyat_text})")
                                    urun_data["fiyat"] = fiyat_text
                                    fiyat_bulundu = True
                                    break
                        except:
                            continue
                    
                    # Strateji 2: Eğer yukarıdakiler çalışmazsa, kart içinde data-test-id içeren etiketleri ara
                    if not fiyat_bulundu:
                        try:
                            # price-current-price içeren etiketleri bul
                            fiyat_elementleri = urun_karti.find_elements(By.XPATH, ".//div[contains(@data-test-id, 'price-current-price')]")
                            
                            for fiyat_elementi in fiyat_elementleri:
                                fiyat_text = fiyat_elementi.text
                                
                                if fiyat_text and ("TL" in fiyat_text or any(c.isdigit() for c in fiyat_text)):
                                    # Ürün puanı değil, gerçek fiyat olup olmadığını kontrol et
                                    if not ("Ürün puanı" in fiyat_text or "değerlendirme" in fiyat_text):
                                        # Fiyat formatını temizle (% işaretini ve sonrasını kaldır)
                                        fiyat_text = re.sub(r'%.*$', '', fiyat_text).strip()
                                        
                                        print(f"Ürün fiyatı (data-test-id): {fiyat_text}")
                                        urun_data["fiyat"] = fiyat_text
                                        fiyat_bulundu = True
                                        break
                        except Exception as e:
                            print(f"Fiyat için data-test-id etiketleri bulunamadı: {str(e)}")
                    
                    # Strateji 3: Tüm fiyat içeren sınıfları dene
                    if not fiyat_bulundu:
                        try:
                            # price class'ı içeren etiketleri bul
                            fiyat_elementleri = urun_karti.find_elements(By.XPATH, ".//*[contains(@class, 'price')]")
                            
                            for fiyat_elementi in fiyat_elementleri:
                                fiyat_text = fiyat_elementi.text
                                
                                if fiyat_text and ("TL" in fiyat_text or any(c.isdigit() for c in fiyat_text)):
                                    # Ürün puanı değil, gerçek fiyat olup olmadığını kontrol et
                                    if not ("Ürün puanı" in fiyat_text or "değerlendirme" in fiyat_text):
                                        # Fiyat formatını temizle (% işaretini ve sonrasını kaldır)
                                        fiyat_text = re.sub(r'%.*$', '', fiyat_text).strip()
                                        
                                        print(f"Ürün fiyatı (price class): {fiyat_text}")
                                        urun_data["fiyat"] = fiyat_text
                                        fiyat_bulundu = True
                                        break
                        except Exception as e:
                            print(f"Fiyat için class içeren etiketler bulunamadı: {str(e)}")
                    
                    # Marka bilgisini bulmayı dene
                    try:
                        marka = urun_karti.find_element(By.XPATH, ".//span[contains(@data-test-id, 'brand')]").text
                        if marka:
                            print(f"Ürün markası: {marka}")
                            urun_data["marka"] = marka
                    except:
                        print("Marka bilgisi alınamadı.")
                    
                    # Ürün verilerini ana JSON'a ekle
                    urun_verileri[f"urun_{i+1}"] = urun_data
                    
                except Exception as e:
                    print(f"Ürün kartı bulunamadı: {str(e)}")
                
            except Exception as e:
                print(f"{i+1}. ürün için hata: {str(e)}")
        
        print("\nTüm ürünler incelendi.")
        
    except Exception as e:
        print(f"Genel bir hata oluştu: {str(e)}")
    
    finally:
        # WebDriver'ı kapat
        if 'driver' in locals():
            driver.quit()
            print("Tarayıcı kapatıldı.")
    
    # JSON verilerini konsola yazdır
    print("\nToplanan ürün verileri (JSON):")
    print(json.dumps(urun_verileri, indent=2, ensure_ascii=False))
    
    # Hiç veri alınamadıysa kullanıcıya bilgi ver
    if not urun_verileri or all(not urun.get("urun_adi") for urun in urun_verileri.values()):
        print("\nUYARI: Hiç ürün verisi alınamadı.")
        print("Önerilen çözüm: Headless modu geçici olarak kapatmak için aşağıdaki satırı yorum satırı haline getirin:")
        print("  chrome_options.add_argument(\"--headless=new\")")
        print("Bu şekilde tarayıcı görünür olacak ve web sitesi daha az olasılıkla bot tespiti yapacaktır.")
    
    # JSON verilerini döndür
    return urun_verileri

# Fonksiyonu çağır ve sonuçları dosyaya kaydet
if __name__ == "__main__":
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        urun_verileri = hepsiburada_urunleri_incele(search_term)
        
        # JSON verilerini dosyaya kaydet
        with open(f"{search_term}_urunler.json", "w", encoding="utf-8") as json_file:
            json.dump(urun_verileri, json_file, indent=2, ensure_ascii=False)
        print(f"\nÜrün verileri '{search_term}_urunler.json' dosyasına kaydedildi.")
    else:
        print("Lütfen bir arama terimi girin.")
        print("Örnek: python hepsiburada_data_gether.py 'laptop'")