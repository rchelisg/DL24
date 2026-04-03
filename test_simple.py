import time
import datetime

print("Starting simple test...")

for i in range(5):
    current_time = datetime.datetime.now().strftime('%M:%S')
    output = f"Test - {current_time}"
    print(output)
    # 写入文件以验证执行
    with open('simple_test.log', 'a') as f:
        f.write(output + '\n')
    time.sleep(1)

print("Test completed")