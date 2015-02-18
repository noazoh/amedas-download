# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re, os, csv, sys, traceback

ROOTPATH = os.path.dirname(__file__)
DOWNLOADPATH = os.path.join(ROOTPATH, "download")


class Fuken(object):
    def __init__(self, fuken_id, fuken_short):
        self.fuken_id = fuken_id
        self.fuken_name = fuken_short
        self.station_dict = {}  #key:区分コード＋観測所ID value:Stationオブジェクト
        
class Station(object):
    def __init__(self, station_id, station_name, f_pre, f_tem, f_sun, station_kbn):
        self.station_kbn = station_kbn
        self.station_id= station_id
        self.station_name = station_name
        self.isExistTemperature = True if f_tem == 'Y' else False
        self.isExistRainfall = True if f_pre == "Y" else False
        self.isExistSunlight = True if f_sun == "Y" else False
        self.elementIndex = None    #ブラウザ上のエレメントのインデックス
        self.result = False
 
    def necessity(self):
        return self.isExistTemperature and \
                self.isExistRainfall and \
                self.isExistSunlight

def unicode_dictReader(utf8_data, **kwargs):
    csv_reader = csv.DictReader(utf8_data, **kwargs)
    for row in csv_reader:
        yield dict([(key, unicode(value, "utf-8")) for key, value in row.iteritems()])

class AmedasDL(unittest.TestCase):
    # 各テストメソッドの最初に実行される処理
    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-web-securitiy')
        # ダウンロードパス
        options.add_experimental_option('prefs', {'download.default_directory': DOWNLOADPATH})
        # chrome selenium driver のパス  
        self.driver = webdriver.Chrome(executable_path='./chromedriver', chrome_options=options)
        self.driver.maximize_window()
        self.driver.implicitly_wait(5)
        self.base_url = "http://www.data.jma.go.jp/"
        self.verificationErrors = []
        self.accept_next_alert = True        
    
    def test_amedas_d_l(self):
        
        #fuken.csvより、府県コードと府県名を取得
        f = open(os.path.join(ROOTPATH, "fuken.csv"), "rb")
        try:
            rows = unicode_dictReader(f)
            fuken_dict = {} #key:fuken_id, value:Fukenオブジェクト
            for row in rows:
                fuken_id = row["fuken_id"]
                fuken_dict[fuken_id] = Fuken(fuken_id, row["fuken_short"])
        finally:
            f.close()

        #station.csvより、各地域コードと観測所の情報を取得
        f = open(os.path.join(ROOTPATH, "stations.csv"), "rb")
        try:
            station_rows = unicode_dictReader(f)
            for row in station_rows:
                station_kbn = row["station_kbn"] 
                station_id = row["station_id"]
                fuken_id = row["fuken_id"]
                fuken_dict[fuken_id].station_dict[station_kbn + station_id] = Station(station_id,
                                                                        row["station_name"], 
                                                                        row["f_pre"], 
                                                                        row["f_tem"], 
                                                                        row["f_sun"],
                                                                        station_kbn)
        finally:
            f.close()
        
        #debug
        for fuken_key in sorted(fuken_dict.keys()):
            fuken = fuken_dict[fuken_key]
            for station_key in sorted(fuken.station_dict.keys()):
                station = fuken.station_dict[station_key]
                print u"KEY={0}:府県コード={1} 府県名={2} 区分={3} 観測所コード={4} 観測所名={5}".format(station_key,
                                                                                     fuken.fuken_id, 
                                                                                     fuken.fuken_name,
                                                                                     station.station_kbn,
                                                                                     station.station_id,
                                                                                     station.station_name)
            
        
        # ドライバを開きブラウザを立ち上げる
        driver = self.driver

        invalid_list = []
        
        for fuken_key in sorted(fuken_dict.keys()):
            
            fuken = fuken_dict[fuken_key]
            print u"---- {0} 開始 ----".format(fuken.fuken_name)
            
            #まず、各府県ごとのクリッカブルマップから、配下の観測所エレメントをスクレイピングする
            try:
                self.scraping(driver, fuken)
            except Exception as ex:
                print u"---- スクレイピングエラー ----"
                info = sys.exc_info()
                print info[0]
                print ex
                tbinfo = traceback.format_tb(info[2])
                for tb in tbinfo:
                    print tb
                    
                #処理エラーリストに追加する
                invalid_list.append([unicode(fuken.fuken_id), unicode(fuken.fuken_name), u"-", u"-", u"-"])
            else:
            
                #観測所ごとダウンロード
                for station in fuken.station_dict.values():
                    print u"観測所：{0} - {1}".format(fuken.fuken_name, station.station_name)
                    if station.necessity() and station.elementIndex is not None:
                        print u"ダウンロード開始"
                        try:
                            self.dl_amedas(driver, fuken.fuken_id, fuken.fuken_name, station)                    
                        except Exception as ex:
                            print u"---- エラー ----"
                            info = sys.exc_info()
                            print info[0]
                            print ex
                            tbinfo = traceback.format_tb(info[2])
                            for tb in tbinfo:
                                print tb
                                
                            #処理エラーリストに追加する
                            invalid_list.append([unicode(fuken.fuken_id), 
                                                 unicode(fuken.fuken_name), 
                                                 unicode(station.station_kbn), 
                                                 unicode(station.station_id), 
                                                 unicode(station.station_name)])
                        else:
                            pass
                    print u"必要：{0} 結果：{1}".format(station.necessity(), station.result)
                    
            print u"---- {0} 終了 ----".format(fuken.fuken_name)

        #処理エラーリストを保存する
        #f = open(os.path.join(DOWNLOADPATH, "invalid.csv"), "wb")
        #try:
        #    writer = csv.writer(f)
        #    writer.writerows(invalid_list)
        #except Exception as ex:
        #    print ex
        #finally:
        #    f.close()
            
        #結果表示
        print u"以下の地点が取得できなかった----------------------------"
        for fuken_key in sorted(fuken_dict.keys()):
            fuken = fuken_dict[fuken_key]
            for station_key in sorted(fuken.station_dict.keys()):
                station = fuken.station_dict[station_key]
                if station.necessity():
                    if not station.result:
                        print u"府県名={0} 観測所名={1}".format(fuken.fuken_name, station.station_name)
        

    def scraping(self, driver, fuken):
        print fuken.fuken_name + u"をスクレイピング"

        driver.get(self.base_url + "risk/obsdl/")
        time.sleep(1)
        
        #【全選択をクリア】ボタンを押して、前回設定値を消す
        driver.find_element_by_id("buttonDelAll").click()
        time.sleep(1)
        
        #「地点を選ぶ」が選択され、日本地図が表示されている状態のはず。
        print "---"
        
        # 地域（府県）を選択
        fuken_element_id = "pr" + fuken.fuken_id
        driver.find_element_by_id(fuken_element_id).click()
        time.sleep(1)
        #ここで観測所が表示されるページへ遷移

        #奇数番目の//div[@id='stationMap']/div[n]/div　を列挙する
        index = 1
        loop = True
        while loop:
            xpath = "//div[@id='stationMap']/div[{0}]/div".format(index)
            print "xpath=" + xpath
            if not self.is_element_present(how="xpath", what=xpath):
                #そんなエレメントは無い
                loop = False
                print u"エレメントがないのでループ抜ける"
            else:
                #エレメントがある
                station_element = driver.find_element_by_xpath(xpath)
                #その配下にあるhiddenに、観測所コードと名称が入っている。
                #観測所コードの区分は小文字で入ってるので大文字に変換する
                station_id = driver.find_element_by_xpath(xpath + "/input[1]").get_attribute("value").upper()
                station_name = driver.find_element_by_xpath(xpath + "/input[2]").get_attribute("value")
                
                print station_id
                print station_name
                
                #観測所コードで、ディクショナリを探す
                if fuken.station_dict.has_key(station_id):
                    print u"辞書にあった"
                    station = fuken.station_dict[station_id]
                    station.elementIndex = index
                else:
                    print u"辞書にない観測所です"

            index += 2

        #「ほかの都道府県を選ぶ」ボタンを押して、ページを戻しておく
        driver.find_element_by_id("buttonSelectStation").click()
        time.sleep(2)


    def dl_amedas(self, driver, fuken_id, fuken_name, station):
        """
        Args:
            driver: ブラウザドライバ
            fuken_id: 府県コード
            fuken_name: 府県名
            station_name: 観測所名
            station_index: 観測所divのインデックス番号
        """

        #ダウンロードパス＝府県名
        path = os.path.join(DOWNLOADPATH, fuken_id + fuken_name)
        if not os.path.exists(path):
            os.makedirs(path)

        #ファイル存在チェック        
        new_file_name = os.path.join(path, u"{0}_{1}.csv".format(fuken_name, station.station_name))
        if os.path.exists(new_file_name):
            print "すでにダウンロード済みなのでスキップします"
            station.result = True
            return
        
        driver.get(self.base_url + "risk/obsdl/")
        time.sleep(2)
        
        #【全選択をクリア】ボタンを押して、前回設定値を消す
        driver.find_element_by_id("buttonDelAll").click()
        time.sleep(1)

        #「地点を選ぶ」が選択され、日本地図が表示されている状態のはず。

        # 地域IDの設定
        fuken_element_id = "pr" + fuken_id
        driver.find_element_by_id(fuken_element_id).click()
        time.sleep(1)

        # 地域の中で何番目かの設定
        xpath = "//div[@id='stationMap']/div[{0}]/div".format(station.elementIndex)
        station = driver.find_element_by_xpath(xpath)
        station.click()
        time.sleep(1)
        
        #地点が選べているかチェック
        selected_station_list = driver.find_element_by_id("selectedStationList")
        #上記div配下に、class="selectedStText"というdivが存在していれば、地点が選べている
        try:
            selected_station_list.find_element_by_class_name("selectedStText")
        except NoSuchElementException as ex:
            raise Exception("地点がクリックできない")

        #［項目を選ぶ］
        driver.find_element_by_id("elementButton").click()
        #データの種類
        #    デフォルトのまま（日別値）
        #過去の平均値との比較オプション
        #    「平年値も表示」はデフォルトのままチェックONとする
        driver.find_element_by_id(u"N年平均").click()
        Select(driver.find_element_by_name("number")).select_by_visible_text("10")
        time.sleep(1)
        
        driver.find_element_by_id("ui-id-2").click()
        driver.find_element_by_id(u"平均気温").click()
        time.sleep(1)
        driver.find_element_by_id("ui-id-3").click()
        driver.find_element_by_id(u"降水量の合計").click()
        time.sleep(1)
        driver.find_element_by_id("ui-id-4").click()
        driver.find_element_by_id(u"日照時間").click() 
        time.sleep(1)        

        #期間
        driver.find_element_by_css_selector("input[type=\"checkbox\"]").click()
        driver.find_element_by_id("periodButton").click()
        time.sleep(1)
        Select(driver.find_element_by_name("iniy")).select_by_visible_text("2014")
        Select(driver.find_element_by_name("inim")).select_by_visible_text("1")
        Select(driver.find_element_by_name("inid")).select_by_visible_text("1")
        Select(driver.find_element_by_name("endy")).select_by_visible_text("2014")
        Select(driver.find_element_by_name("endm")).select_by_visible_text("12")
        Select(driver.find_element_by_name("endd")).select_by_visible_text("31")
        time.sleep(1)
        
        #【CSVファイルをダウンロード】ボタン
        driver.find_element_by_xpath("//*[@id='csvdl']/img").click()
        time.sleep(3)
        
        #alertが出てないかチェック
        if self.is_alert_present():
            alert_text = self.close_alert_and_get_its_text()
            raise Exception("alertが出てる")
        else:
            # ダウンロードしたファイルをリネーム
            old_file_name = os.path.join(DOWNLOADPATH, 'data.csv')
            if os.path.exists(old_file_name):
                os.rename(old_file_name, new_file_name)
                station.result = True
                time.sleep(2)
            else:
                raise Exception("data.csvファイルがダウンロードできてない")


    def is_element_present(self, how, what):
        try: self.driver.find_element(by=how, value=what)
        except NoSuchElementException: 
            print u"elementがない"
            return False
        return True
    
    def is_alert_present(self):
        try: 
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
        except NoAlertPresentException: 
            print u"alertがない"
            return False
        return True
    
    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True
    
    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
