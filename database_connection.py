import json
import pyodbc
import bcrypt
import pandas as pd
from datetime import datetime

class DataConnection:
    def __init__(self, config_file='config.json'):
        # Đọc thông tin cấu hình từ file JSON
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.connection_string = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={config['server']};"
            f"DATABASE={config['database']};"
            f"UID={config['username']};"
            f"PWD={config['password']}"
        )
        self.conn = None
        self.connect()  # Tự động kết nối khi khởi tạo

    def connect(self):
        try:
            self.conn = pyodbc.connect(self.connection_string)
            print("Kết nối thành công!")
        except Exception as e:
            print("Lỗi kết nối:", e)

    def fetch_data(self, query):
        if self.conn is None:
            print("Chưa kết nối đến cơ sở dữ liệu.")
            return None
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def close(self):
        if self.conn:
            self.conn.close()
            print("Kết nối đã được đóng.")

    def create_tables(self):
        cursor = self.conn.cursor()

        # Tạo bảng User (phải được tạo trước bảng Review)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='User' AND xtype='U')
        BEGIN
            CREATE TABLE [User] (
                UserID INT PRIMARY KEY IDENTITY(1,1),
                Username VARCHAR(100),
                Email VARCHAR(255),
                Password VARCHAR(255),
                JoinDate DATETIME
            )
        END;
        """)

        # Tạo bảng Category
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Category' AND xtype='U')
        BEGIN
            CREATE TABLE Category (
                CategoryID INT PRIMARY KEY IDENTITY(1,1),
                CategoryName VARCHAR(100),
                Description TEXT
            )
        END;
        """)
        

        # Tạo bảng Location
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Location' AND xtype='U')
        BEGIN
            CREATE TABLE Location (
                LocationID INT PRIMARY KEY IDENTITY(1,1),
                LocationName VARCHAR(255),
                Description TEXT,
                Address VARCHAR(255),
                City VARCHAR(100),
                Country VARCHAR(100),
                Latitude DECIMAL(10, 8),
                Longitude DECIMAL(11, 8),
                CategoryID INT,
                OpeningHours VARCHAR(50),
                Contact VARCHAR(50),
                Rating DECIMAL(2, 1),
                Website VARCHAR(255),
                FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID)
            )
        END;
        """)

        # Tạo bảng Review (phải tạo sau bảng User và Location)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Review' AND xtype='U')
        BEGIN
            CREATE TABLE Review (
                ReviewID INT PRIMARY KEY IDENTITY(1,1),
                LocationID INT,
                UserID INT,
                Rating DECIMAL(2, 1),
                Comment TEXT,
                ReviewDate DATETIME,
                FOREIGN KEY (LocationID) REFERENCES [Location](LocationID),
                FOREIGN KEY (UserID) REFERENCES [User](UserID)
            )
        END;
        """)

        # Tạo bảng Image
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Image' AND xtype='U')
        BEGIN
            CREATE TABLE Image (
                ImageID INT PRIMARY KEY IDENTITY(1,1),
                LocationID INT,
                ImageURL VARCHAR(255),
                Description TEXT,
                FOREIGN KEY (LocationID) REFERENCES [Location](LocationID)
            )
        END;
        """)

        # Tạo bảng Event
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Event' AND xtype='U')
        BEGIN
            CREATE TABLE Event (
                EventID INT PRIMARY KEY IDENTITY(1,1),
                LocationID INT,
                EventName VARCHAR(255),
                EventDate DATETIME,
                Description TEXT,
                TicketPrice DECIMAL(10, 2),
                FOREIGN KEY (LocationID) REFERENCES [Location](LocationID)
            )
        END;
        """)

        # Tạo bảng Tour
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Tour' AND xtype='U')
        BEGIN
            CREATE TABLE Tour (
                TourID INT PRIMARY KEY IDENTITY(1,1),
                TourName VARCHAR(255),
                LocationID INT,
                StartDate DATETIME,
                EndDate DATETIME,
                Price DECIMAL(10, 2),
                GuideID INT,
                FOREIGN KEY (LocationID) REFERENCES [Location](LocationID)
            )
        END;
        """)

        # Tạo bảng Location_Amenities
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Location_Amenities' AND xtype='U')
        BEGIN
            CREATE TABLE Location_Amenities (
                LocationID INT,
                AmenityID INT,
                AmenityName VARCHAR(100),
                Description TEXT,
                FOREIGN KEY (LocationID) REFERENCES [Location](LocationID)
            )
        END;
        """)

        self.conn.commit()
        cursor.close()

    def save_conversation(self, user_input, bot_response):
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO conversations (user_input, bot_response) VALUES (?, ?)", (user_input, bot_response))
        self.conn.commit()
        cursor.close()
        self.close()

    def register_user(self, username, email, password):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO [User] (Username, Email, Password, JoinDate) VALUES (?, ?, ?, ?)",
                    (username, email, password, datetime.now()))
        self.conn.commit()
        cursor.close()


    def authenticate_user(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute("SELECT Password FROM [User] WHERE Username = ?", (username,))
        result = cursor.fetchone()
        cursor.close()
        
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            return True
        return False

    
    def check_user_exists(self, username, email):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM [User] WHERE Username = ? OR Email = ?", (username, email))
        result = cursor.fetchone()
        cursor.close()
        return result is not None  # Trả về True nếu người dùng đã tồn tại

    
    def import_data(self, file_path):
        df = pd.read_csv(file_path)
        cursor = self.conn.cursor()
        for index, row in df.iterrows():
            cursor.execute("INSERT INTO Location (LocationName, Description, Address, City, Country, Latitude, Longitude, CategoryID, OpeningHours, Contact, Rating, Website) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (row['LocationName'], row['Description'], row['Address'], row['City'], row['Country'], row['Latitude'], row['Longitude'], row['CategoryID'], row['OpeningHours'], row['Contact'], row['Rating'], row['Website']))
        self.conn.commit()
        cursor.close()

    def export_data(self, table_name, file_path):
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, self.conn)
        df.to_csv(file_path, index=False)

    def get_answer_from_knowledge_base(self, user_input):
        """
        Truy xuất câu trả lời từ cơ sở dữ liệu dựa trên câu hỏi của người dùng
        """
        cursor = self.conn.cursor()
        
        # Tìm kiếm câu hỏi gần đúng với input của người dùng
        query = """
        SELECT Answer FROM KnowledgeBase
        WHERE Question LIKE ? 
        """
        cursor.execute(query, ('%' + user_input + '%',))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return result[0]  # Trả về câu trả lời
        else:
            return None  # Nếu không tìm thấy câu trả lời

# # Ví dụ sử dụng
# if __name__ == "__main__":
#     db = DataConnection()
#     db.connect()
#     data = db.fetch_data("SELECT * FROM Location")  # Thay thế bằng tên bảng của bạn
#     for row in data:
#         print(row)
#     db.close()
