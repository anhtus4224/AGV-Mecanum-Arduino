"""Build actual ATmega2560 ELF/HEX using an existing AVR toolchain and Arduino AVR core.
Usage: python3 build_avr.py TOOLCHAIN_BIN ARDUINO_AVR_ROOT OUTPUT_DIR
No upload or serial access. No Arduino stub is used.
"""
import sys,subprocess,os
from pathlib import Path
binpath,corepath,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[1]
common=['-Os','-ffunction-sections','-fdata-sections','-mmcu=atmega2560','-DF_CPU=16000000L','-DARDUINO=10819','-DARDUINO_AVR_MEGA2560','-DARDUINO_ARCH_AVR','-I'+str(corepath/'cores/arduino'),'-I'+str(corepath/'variants/mega')]
objects=[]
for p in sorted((corepath/'cores/arduino').iterdir()):
 if p.suffix not in ('.c','.cpp','.S'):continue
 target=out/(p.name+'.o');tool='avr-g++' if p.suffix=='.cpp' else 'avr-gcc'
 extra=['-std=gnu++11','-fno-exceptions','-fno-threadsafe-statics'] if p.suffix=='.cpp' else ['-std=gnu11'] if p.suffix=='.c' else ['-x','assembler-with-cpp']
 subprocess.run([str(binpath/tool)]+common+extra+['-c',str(p),'-o',str(target)],check=True);objects.append(str(target))
p=root/'mega_vector_v1/mega_vector_v1.ino';target=out/'sketch.o'
subprocess.run([str(binpath/'avr-g++')]+common+['-std=gnu++11','-fno-exceptions','-fno-threadsafe-statics','-x','c++','-c',str(p),'-o',str(target)],check=True)
elf=out/'mega_vector_v1.elf'
subprocess.run([str(binpath/'avr-g++'),'-mmcu=atmega2560','-Wl,--gc-sections',str(target)]+objects+['-lm','-o',str(elf)],check=True)
subprocess.run([str(binpath/'avr-objcopy'),'-O','ihex','-R','.eeprom',str(elf),str(out/'mega_vector_v1.hex')],check=True)
subprocess.run([str(binpath/'avr-size'),'-C','--mcu=atmega2560',str(elf)],check=True)
