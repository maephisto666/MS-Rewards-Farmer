import getpass
import os
import subprocess
from datetime import datetime

# 取得當前使用者的名稱
current_user = getpass.getuser()


# 取得當前使用者的SID
def get_user_sid(username):
    try:
        output = subprocess.check_output(
            f'wmic useraccount where name="{username}" get sid', shell=True
        )
        sid = output.decode().split("\n")[1].strip()
        return sid
    except Exception as e:
        print(f"Error getting SID for user {username}: {e}")
        return None


current_user_sid = get_user_sid(current_user)
computer_name = os.environ["COMPUTERNAME"]

# Let the user choose between Miniconda and Anaconda
print("Please choose your Python distribution:")
print("1. Miniconda")
print("2. Anaconda")
choice = input("Enter your choice (1 or 2): ")

if choice == "1":
    base_path = f"C:\\Users\\{current_user}\\miniconda3"
elif choice == "2":
    base_path = f"C:\\Users\\{current_user}\\anaconda3"
else:
    print("Invalid choice, please rerun the script and choose 1 or 2.")
    exit(1)

# Let the user enter the name of the environment they are using
env_name = input("Please enter the name of the environment you are using: ")

# Use the current working directory as the output path
output_path = os.path.join(os.getcwd(), "MS_reward.xml")
print(f"The XML file will be saved to: {output_path}")


xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{datetime.utcnow().isoformat()}</Date>
    <Author>{computer_name}\\{current_user}</Author>
    <URI>\\Custom\\MS reward</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-07-03T06:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{current_user_sid}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>%windir%\\System32\\cmd.exe</Command>
      <Arguments>/K "{base_path}\\Scripts\\activate.bat {base_path} &amp;&amp; conda activate {env_name} &amp;&amp; {os.getcwd()}\\MS_reward.bat"</Arguments>
      <WorkingDirectory>{os.getcwd()}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""


with open(output_path, "w", encoding="utf-16") as file:
    file.write(xml_content)

print(f"XML file has been generated and saved to: {output_path}")
