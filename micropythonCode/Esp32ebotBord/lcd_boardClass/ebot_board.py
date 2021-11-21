from machine import Pin, SoftI2C
import time
import ssd1306

class EbotBoard():
    def __init__(self, 
                oled_i2c_SDA_pin = 21,
                oled_i2c_SCL_pin = 22,
                IN1_pin = 15,
                IN2_pin = 2,
                IN3_pin = 4,
                IN4_pin = 5,
                ENA_pin = 23,
                ENB_pin = 12,
                btn1_pin = 16,  # conecta no 3.3v ao ser pressionado, precisa de PULL-DOWN
                btn2_pin = 17,  # conecta no 3.3v ao ser pressionado, precisa de PULL-DOWN
                btn3_pin = 18,  # conecta no 3.3v ao ser pressionado, precisa de PULL-DOWN
                qtr_pins = [14, 27, 26, 25, 33, 32, 35, 34, 13] # ir1, ir2, ..., ir8, ledOn
                ):
        self.oled_i2c_SDA_pin = oled_i2c_SDA_pin
        self.oled_i2c_SCL_pin = oled_i2c_SCL_pin
        self.IN1_pin = IN1_pin
        self.IN2_pin = IN2_pin
        self.IN3_pin = IN3_pin
        self.IN4_pin = IN4_pin
        self.ENA_pin = ENA_pin
        self.ENB_pin = ENB_pin
        self.btn1_pin = btn1_pin
        self.btn2_pin = btn2_pin
        self.btn3_pin = btn3_pin
        self.qtr_pins = qtr_pins
        self.start_lcd()
        self.clear_lcd()
        time.sleep(2)
        self.write_text("EBOT IFSP Pira", 0)
        self.write_text("LCD Iniciado", 1)
        self.write_text("Aguardando BT", 2)


    def start_lcd(self):
        self.i2c = SoftI2C(sda=Pin(self.oled_i2c_SDA_pin), scl=Pin(self.oled_i2c_SCL_pin))
        self.display = ssd1306.SSD1306_I2C(128, 64, self.i2c)
        
    def clear_lcd(self):
        self.display.fill(0)
        self.display.show()

    def write_text(self, txt, linha=0):
        self.display.text(txt, 0, 15*linha + 2, 1)
        self.display.show()

    def botao1(self):
        pass  #TODO implementar instancia e metodos de leitura automaticos aqui para facilidar

    def botao2(self):
        pass  #TODO implementar instancia e metodos de leitura automaticos aqui para facilidar

    def botao3(self):
        pass  #TODO implementar instancia e metodos de leitura automaticos aqui para facilidar

    def qtr8(self):
        pass  #TODO Implementar biblioteca do qtr8