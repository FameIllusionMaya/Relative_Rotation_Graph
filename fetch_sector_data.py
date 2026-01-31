
from tvDatafeed import TvDatafeed, Interval
tv = TvDatafeed()

# หมวดธุรกิจ (Sectors) - 29 หมวด
sectors = [
    "SET",
    # กลุ่มเกษตรและอุตสาหกรรมอาหาร
    "AGRI",      # ธุรกิจการเกษตร
    "FOOD",      # อาหารและเครื่องดื่ม
    
    # กลุ่มสินค้าอุปโภคบริโภค
    "FASHION",   # แฟชั่น
    "HOME",      # ของใช้ในครัวเรือนและสำนักงาน
    "PERSON",    # ของใช้ส่วนตัวและเวชภัณฑ์
    
    # กลุ่มธุรกิจการเงิน
    "BANK",      # ธนาคาร
    "FIN",       # เงินทุนและหลักทรัพย์
    "INSUR",     # ประกันภัยและประกันชีวิต
    
    # กลุ่มสินค้าอุตสาหกรรม
    "AUTO",      # ยานยนต์
    "IMM",       # วัสดุอุตสาหกรรมและเครื่องจักร
    "PAPER",     # กระดาษและวัสดุการพิมพ์
    "PETRO",     # ปิโตรเคมีและเคมีภัณฑ์
    "PKG",       # บรรจุภัณฑ์
    "STEEL",     # เหล็กและผลิตภัณฑ์โลหะ
    
    # กลุ่มอสังหาริมทรัพย์และก่อสร้าง
    "CONMAT",    # วัสดุก่อสร้าง
    "CONS",      # บริการรับเหมาก่อสร้าง
    "PF_REIT",  # กองทุนรวมอสังหาริมทรัพย์และกองทรัสต์
    "PROP",      # พัฒนาอสังหาริมทรัพย์
    
    # กลุ่มทรัพยากร
    "ENERG",     # พลังงานและสาธารณูปโภค
    "MINE",      # เหมืองแร่
    
    # กลุ่มบริการ
    "COMM",      # พาณิชย์
    "HELTH",     # การแพทย์
    "MEDIA",     # สื่อและสิ่งพิมพ์
    "PROF",      # บริการเฉพาะกิจ
    "TOURISM",   # การท่องเที่ยวและสันทนาการ
    "TRANS",     # ขนส่งและโลจิสติกส์
    
    # กลุ่มเทคโนโลยี
    "ETRON",     # ชิ้นส่วนอิเล็กทรอนิกส์
    "ICT"        # เทคโนโลยีสารสนเทศและการสื่อสาร
]

# sectors = ["SET"]


import time
from datetime import datetime

def fetch_with_retry(symbol, exchange='SET', interval=Interval.in_daily, n_bars=5000, max_retries=3, wait_time=20):
    """
    Fetch stock data with retry mechanism
    
    Args:
        symbol: Stock symbol
        exchange: Exchange name
        interval: Time interval
        n_bars: Number of bars to fetch
        max_retries: Maximum number of retry attempts
        wait_time: Wait time in seconds before retry
    
    Returns:
        DataFrame or None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            print(f"Fetching {symbol} (Attempt {attempt + 1}/{max_retries})...")
            stock_data = tv.get_hist(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                n_bars=n_bars
            )
            
            # Check if data is valid
            if stock_data is not None and not stock_data.empty:
                print(f"✓ Successfully fetched {symbol} - {len(stock_data)} rows")
                return stock_data
            else:
                print(f"✗ No data returned for {symbol}")
                
        except Exception as e:
            print(f"✗ Error fetching {symbol}: {str(e)}")
        
        # Wait before retry (except for the last attempt)
        if attempt < max_retries - 1:
            print(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    print(f"⚠ Failed to fetch {symbol} after {max_retries} attempts")
    return None


# Main execution
failed_symbols = []
successful_symbols = []

for symbol in sectors:
    print(f"\n{'='*60}")
    print(f"Processing: {symbol}")
    print(f"{'='*60}")
    
    stock_data = fetch_with_retry(symbol, wait_time=20, max_retries=3)
    
    if stock_data is not None:
        try:
            filename = f'{symbol}.csv'
            stock_data.to_csv(filename)
            print(f"✓ Saved to {filename}")
            successful_symbols.append(symbol)
        except Exception as e:
            print(f"✗ Error saving {symbol}: {str(e)}")
            failed_symbols.append(symbol)
    else:
        failed_symbols.append(symbol)
    
    # Small delay between symbols to avoid rate limiting
    time.sleep(2)

# Summary
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"Total symbols: {len(sectors)}")
print(f"Successful: {len(successful_symbols)}")
print(f"Failed: {len(failed_symbols)}")

if failed_symbols:
    print(f"\nFailed symbols: {', '.join(failed_symbols)}")
