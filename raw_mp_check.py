import multiprocessing
import time

def worker(num):
    print(f"Worker {num} starting...")
    time.sleep(1)
    return num * 2

if __name__ == "__main__":
    print("Main process starting...")
    with multiprocessing.Pool(processes=2) as pool:
        res = pool.map(worker, [1, 2, 3])
    print(f"Main process received: {res}")
