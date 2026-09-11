"""Create a portable source ZIP from tracked files, excluding hosting identity."""
import pathlib,subprocess,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
target=root/'public/phoenix-neighborhood-map-source.zip'
target_name=target.relative_to(root).as_posix()
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in files:
  if not name or name.startswith('.openai/') or name==target_name:continue
  z.write(root/name,'phoenix-neighborhood-map/'+name)
print(f'{target}: {target.stat().st_size} bytes')

