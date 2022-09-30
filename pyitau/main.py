import json

import requests
from selenium.common import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from pyitau.pages import (CardDetails, CardsPage, CheckingAccountFullStatement,
                          CheckingAccountMenu, CheckingAccountStatementsPage,
                          DropdownMenu, FirstRouterPage, MenuPage,
                          PasswordPage, SecondRouterPage)

ROUTER_URL = 'https://internetpf5.itau.com.br/router-app/router'


class Itau:
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
    }

    def __init__(self, agency, account, account_digit, password, webdriver=None):
        self.agency = agency
        self.account = account
        self.account_digit = account_digit
        self.password = password
        self._session = requests.Session()
        self._session.headers = {
            **self._session.headers,
            **self.headers,
        }

        self._webdriver = webdriver

    def authenticate(self):
        if self._webdriver is not None:
            print('Initializing autentication')
            self._webdriver.get('https://itau.com.br')
            WebDriverWait(self._webdriver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "form_login"))
            )
            agency_el = self._webdriver.find_element(By.ID, 'agencia')
            account_el = self._webdriver.find_element(By.ID, 'conta')
            login_button_xpath = '//form[@class="form_login"]//button[@type="submit"]'
            login_button_el = self._webdriver.find_element(By.XPATH,
                                                           login_button_xpath)
            agency_el.send_keys(self.agency)
            account_el.send_keys(f'{self.account}{self.account_digit}')
            self.__close_popup_and_click(login_button_el)
            print('Authenticating with password')
            keyboard = WebDriverWait(self._webdriver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'teclado'))
            )
            keys = keyboard.find_element(By.CLASS_NAME, 'teclas')
            all_keys_el = keys.find_elements(By.CLASS_NAME, 'campoTeclado')
            mapper = {}
            for key_el in all_keys_el:
                numbers = key_el.get_attribute('aria-label').split(' ou ')
                mapper[numbers[0]] = key_el
                mapper[numbers[1]] = key_el
            for letter in self.password:
                self.__close_popup_and_click(mapper[letter])
            login_button_el = self._webdriver.find_element(By.ID, 'acessar')
            self.__close_popup_and_click(login_button_el)
            print('Authentication complete')
            return

        self._authenticate2()
        self._authenticate3()
        self._authenticate4()
        self._authenticate5()
        self._authenticate6()
        self._authenticate7()
        self._authenticate8()
        self._authenticate9()

    def __wait_until_and_remove_popup(self, condition, timeout):
        try:
            return WebDriverWait(self._webdriver, timeout).until(condition)
        except Exception:
            actions = ActionChains(self._webdriver)
            actions.w3c_actions.pointer_action.move_to_location(0, 0)
            actions.click().perform()
            return WebDriverWait(self._webdriver, timeout).until(condition)

    def __close_popup_and_click(self, element):
        try:
            element.click()
        except Exception:
            actions = ActionChains(self._webdriver)
            actions.w3c_actions.pointer_action.move_to_location(0, 0)
            actions.click().click().click().click()

            actions.perform()
            self.__close_popup_and_click(element)

    def _load_cards(self):
        self.__wait_until_and_remove_popup(
            EC.element_to_be_clickable((By.ID, 'boxContaCorrente')),
            5
        )

        cards_accordion_link = self.__wait_until_and_remove_popup(
            EC.element_to_be_clickable((By.ID, 'boxCartoes')),
            5
        )

        self.__close_popup_and_click(cards_accordion_link)
        print('Retrieving cards')
        WebDriverWait(self._webdriver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//a[@title="ver fatura cartão"]'))
        )

    def _get_credit_card_invoice_webdriver(self):
        print('Waiting home rendering')
        chain = ActionChains(self._webdriver)
        for i in range(5):
            chain.send_keys(Keys.ESCAPE)
        chain.perform()
        self._load_cards()

        total_cards = len(self._webdriver.find_elements(By.XPATH,
                                                        '//a[@title="ver fatura cartão"]'))
        output = {}
        for card_i in range(total_cards):
            all_cards = self._webdriver.find_elements(By.XPATH,
                                                      '//a[@title="ver fatura cartão"]')
            self.__close_popup_and_click(all_cards[card_i])
            print(f'Going to #{card_i} card details')

            print(self._webdriver.page_source)
            try:
                WebDriverWait(self._webdriver, 30).until(
                    EC.element_to_be_clickable((By.XPATH,
                                                "//button[contains(@aria-label, 'imprimir')]"))
                )
            except TimeoutException:
                pass
            card_details_request = []
            for r in self._webdriver.requests[::-1]:
                if r.url.endswith('/router') and r.params.get('secao') == 'Cartoes:MinhaFatura':
                    card_details_request.append(r)
            card_details_request = card_details_request[0]
            card_data = json.loads(card_details_request.response.body)
            output[card_data['object']['data'][card_i]['numero']] = card_data
            home_el = self._webdriver.find_element(By.XPATH, '//a[@title="Home"]')
            self.__close_popup_and_click(home_el)
            self._load_cards()
        return output

    def get_credit_card_invoice(self):
        if self._webdriver is not None:
            return self._get_credit_card_invoice_webdriver()

        response = self._session.post(ROUTER_URL, headers={'op': self._home.dropdown_menu_op})

        dropdown_menu = DropdownMenu(response.text)
        __headers = {'op': dropdown_menu.bill_and_limit_op,
                     'X-Auth-Token': response.headers['X-Auth-Token']}
        response = self._session.post(ROUTER_URL, headers=__headers)

        cards_page = CardsPage(response.text)
        __headers = {'op': cards_page.card_details_op,
                     'X-Auth-Token': response.headers['X-Auth-Token']}
        response = self._session.post(ROUTER_URL, headers=__headers,
                                      data={'idCartao': cards_page.first_card_id, 'op': ''})

        card_details = CardDetails(response.text)
        __headers = {'op': card_details.full_invoice_op,
                     'X-Auth-Token': response.headers['X-Auth-Token']}
        response = self._session.post(ROUTER_URL, headers=__headers,
                                      data={'secao': 'Cartoes:MinhaFatura',
                                            'item': ''})
        return response.json()

    def get_statements(self):
        headers = {'op': self._home.op, 'segmento': 'VAREJO'}

        response = self._session.post(ROUTER_URL, headers=headers)
        menu = MenuPage(response.text)

        response = self._session.post(ROUTER_URL, headers={'op': menu.checking_account_op})
        account_menu = CheckingAccountMenu(response.text)

        response = self._session.post(ROUTER_URL, headers={'op': account_menu.statements_op})
        statements_page = CheckingAccountStatementsPage(response.text)

        response = self._session.post(
            ROUTER_URL,
            headers={'op': statements_page.full_statement_op},
        )
        full_statement_page = CheckingAccountFullStatement(response.text)

        response = self._session.post(
            ROUTER_URL,
            data={'periodoConsulta': 90},
            headers={'op': full_statement_page.filter_statements_op},
        )
        return response.json()

    def _authenticate2(self):
        data = {
            'portal': '005',
            'pre-login': 'pre-login',
            'tipoLogon': '7',
            'usuario.agencia': self.agency,
            'usuario.conta': self.account,
            'usuario.dac': self.account_digit,
            'destino': '',
        }
        response = self._session.post(ROUTER_URL, data=data)
        page = FirstRouterPage(response.text)
        self._session.cookies.set('X-AUTH-TOKEN', page.auth_token)
        # if self._webdriver is not None:
        #     self._webdriver.add_cookie({'name': 'X-AUTH-TOKEN', 'value': page.auth_token})
        self._op2 = page.secapdk
        self._op3 = page.secbcatch
        self._op4 = page.perform_request
        self._flow_id = page.flow_id
        self._client_id = page.client_id
        self._auth_token = page.auth_token

    def _authenticate3(self):
        headers = {
            'op': self._op2,
            'X-FLOW-ID': self._flow_id,
            'X-CLIENT-ID': self._client_id,
            'renderType': 'parcialPage',
            'X-Requested-With': 'XMLHttpRequest',
        }

        self._session.post(ROUTER_URL, headers=headers)

    def _authenticate4(self):
        headers = {'op': self._op3}
        self._session.post(ROUTER_URL, headers=headers)

    def _authenticate5(self):
        headers = {'op': self._op4}
        response = self._session.post(ROUTER_URL, headers=headers)
        page = SecondRouterPage(response.text)
        self._op5 = page.op_sign_command
        self._op6 = page.op_maquina_pirata
        self._op7 = page.guardiao_cb

    def _authenticate6(self):
        headers = {'op': self._op5}
        self._session.post(ROUTER_URL, headers=headers)

    def _authenticate7(self):
        headers = {'op': self._op6}
        self._session.post(ROUTER_URL, headers=headers)

    def _authenticate8(self):
        headers = {'op': self._op7}
        response = self._session.post(ROUTER_URL, headers=headers)
        page = PasswordPage(response.text)

        self._op8 = page.op
        self._letter_password = page.letter_password(self.password)

    def _authenticate9(self):
        headers = {'op': self._op8}
        data = {
            'op': self._op8,
            'senha': self._letter_password
        }

        response = self._session.post(ROUTER_URL, headers=headers, data=data)
        if self._webdriver is not None:
            self._webdriver.get("data:text/html;charset=utf-8," + response.text)
        # self._home = AuthenticatedHomePage(response.text)
