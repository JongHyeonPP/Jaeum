import os
import urllib.request
import zipfile
import shutil

TOOLS_DIR = "tools"

def download_and_extract(url, zip_name, target_file_map):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Downloading {zip_name} from {url}...")
    try:
        with urllib.request.urlopen(req) as response, open(zip_name, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        print("Extracting...")
        with zipfile.ZipFile(zip_name, 'r') as zip_ref:
            # Check for nested dirs
            file_list = zip_ref.namelist()
            
            for target_name, dest_name in target_file_map.items():
                # Find the actual path in zip (could be in subdir)
                found = None
                for f in file_list:
                    if f.endswith(target_name):
                        found = f
                        break
                
                if found:
                    with zip_ref.open(found) as source, open(os.path.join(TOOLS_DIR, dest_name), "wb") as target:
                        shutil.copyfileobj(source, target)
                    print(f"Installed tools/{dest_name}")
                else:
                    print(f"Warning: {target_name} not found in zip.")

        os.remove(zip_name)
    except Exception as e:
        print(f"Error handling {zip_name}: {e}")

def setup():
    if not os.path.exists(TOOLS_DIR):
        os.makedirs(TOOLS_DIR)

    # 1. NASM
    download_and_extract(
        "https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip",
        "nasm.zip",
        {"nasm.exe": "nasm.exe"}
    )

    # 2. GoLink
    download_and_extract(
        "http://www.godevtool.com/Golink.zip",
        "golink.zip",
        {"golink.exe": "golink.exe", "GoLink.exe": "golink.exe"} # Case insensitive match logic not implemented, providing options
    )

if __name__ == "__main__":
    setup()
