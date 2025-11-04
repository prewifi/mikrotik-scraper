"""
SFTP client for secure file transfer.

This module provides a secure SFTP client for uploading and downloading
backup files from Mikrotik routers using SSH/SFTP protocol.
"""

import logging
from pathlib import Path
from typing import Optional

import paramiko
from paramiko import SSHClient, AutoAddPolicy, SFTPClient

logger = logging.getLogger(__name__)


class SFTPClientManager:
    """
    SFTP client manager for secure file transfer.

    This class handles secure file transfer operations to and from
    Mikrotik routers using SFTP protocol via SSH.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        timeout: int = 10,
    ):
        """
        Initialize the SFTP client manager.

        Parameters:
            host (str): Router IP address or hostname.
            username (str): SSH username.
            password (str): SSH password.
            port (int): SSH port (default: 22).
            timeout (int): Connection timeout in seconds (default: 10).
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.ssh_client: Optional[SSHClient] = None
        self.sftp_client: Optional[SFTPClient] = None

    def connect(self) -> bool:
        """
        Establish SFTP connection to the router.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port} via SFTP...")

            # Create SSH client
            self.ssh_client = SSHClient()
            self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())

            # Connect to router
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )

            # Open SFTP session
            self.sftp_client = self.ssh_client.open_sftp()

            logger.info(f"Successfully connected to {self.host} via SFTP")
            return True

        except paramiko.AuthenticationException as e:
            logger.error(f"Authentication failed for {self.host}: {e}")
            self.disconnect()
            return False
        except paramiko.SSHException as e:
            logger.error(f"SSH error connecting to {self.host}: {e}")
            self.disconnect()
            return False
        except Exception as e:
            logger.error(f"Failed to connect to {self.host} via SFTP: {e}")
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Close the SFTP and SSH connections."""
        try:
            if self.sftp_client:
                self.sftp_client.close()
                self.sftp_client = None
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
            logger.info(f"Disconnected from {self.host}")
        except Exception as e:
            logger.warning(f"Error disconnecting from {self.host}: {e}")

    def execute_command(self, command: str, timeout: int = 30) -> tuple[bool, str, str]:
        """
        Execute a command on the router via SSH.

        Parameters:
            command (str): Command to execute.
            timeout (int): Command execution timeout in seconds (default: 30).

        Returns:
            tuple[bool, str, str]: (Success status, stdout, stderr).
        """
        if not self.ssh_client:
            logger.error("SSH client not connected")
            return False, "", "SSH client not connected"

        try:
            logger.info(f"Executing command on {self.host}: {command}")
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                logger.info(f"Command executed successfully on {self.host}")
                return True, stdout_text, stderr_text
            else:
                logger.warning(f"Command failed on {self.host} with exit status {exit_status}")
                return False, stdout_text, stderr_text
                
        except Exception as e:
            logger.error(f"Error executing command on {self.host}: {e}")
            return False, "", str(e)

    def upload_file(
        self, local_path: str, remote_path: str, create_remote_dirs: bool = True
    ) -> bool:
        """
        Upload a file to the router via SFTP.

        Parameters:
            local_path (str): Path to local file.
            remote_path (str): Remote destination path.
            create_remote_dirs (bool): Create remote directories if they don't exist.

        Returns:
            bool: True if upload successful, False otherwise.
        """
        if not self.sftp_client:
            logger.error("SFTP client not connected")
            return False

        try:
            local_file = Path(local_path)
            if not local_file.exists():
                logger.error(f"Local file not found: {local_path}")
                return False

            # Create remote directories if needed
            if create_remote_dirs:
                remote_dir = str(Path(remote_path).parent)
                self._create_remote_dirs(remote_dir)

            # Upload file
            self.sftp_client.put(str(local_path), remote_path)
            logger.info(f"Uploaded {local_path} to {self.host}:{remote_path}")
            return True

        except Exception as e:
            logger.error(f"Error uploading file to {self.host}: {e}")
            return False

    def download_file(
        self, remote_path: str, local_path: str, create_local_dirs: bool = True
    ) -> bool:
        """
        Download a file from the router via SFTP.

        Parameters:
            remote_path (str): Remote file path.
            local_path (str): Local destination path.
            create_local_dirs (bool): Create local directories if they don't exist.

        Returns:
            bool: True if download successful, False otherwise.
        """
        if not self.sftp_client:
            logger.error("SFTP client not connected")
            return False

        try:
            # Create local directories if needed
            if create_local_dirs:
                local_dir = Path(local_path).parent
                local_dir.mkdir(parents=True, exist_ok=True)

            # Download file
            self.sftp_client.get(remote_path, str(local_path))
            logger.info(f"Downloaded {remote_path} from {self.host} to {local_path}")
            return True

        except FileNotFoundError as e:
            logger.error(f"Remote file not found on {self.host}: {remote_path}")
            return False
        except Exception as e:
            logger.error(f"Error downloading file from {self.host}: {e}")
            return False

    def list_files(self, remote_path: str = ".") -> Optional[list]:
        """
        List files in a remote directory.

        Parameters:
            remote_path (str): Remote directory path (default: ".").

        Returns:
            Optional[list]: List of file names, or None if error occurs.
        """
        if not self.sftp_client:
            logger.error("SFTP client not connected")
            return None

        try:
            files = self.sftp_client.listdir(remote_path)
            logger.debug(f"Listed {len(files)} files in {remote_path}")
            return files
        except Exception as e:
            logger.error(f"Error listing files from {self.host}: {e}")
            return None

    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a remote file exists.

        Parameters:
            remote_path (str): Remote file path.

        Returns:
            bool: True if file exists, False otherwise.
        """
        if not self.sftp_client:
            logger.error("SFTP client not connected")
            return False

        try:
            self.sftp_client.stat(remote_path)
            return True
        except IOError:
            return False

    def _create_remote_dirs(self, remote_path: str) -> None:
        """
        Create remote directories recursively if they don't exist.

        Parameters:
            remote_path (str): Remote directory path.
        """
        if not self.sftp_client:
            return

        try:
            # Check if path exists
            try:
                self.sftp_client.stat(remote_path)
                return  # Path already exists
            except IOError:
                pass  # Path doesn't exist, create it

            # Split path into parts
            parts = Path(remote_path).parts
            current_path = ""

            for part in parts:
                if part == "/":
                    current_path = "/"
                    continue
                current_path = str(Path(current_path) / part)

                # Try to create directory
                try:
                    self.sftp_client.mkdir(current_path)
                    logger.debug(f"Created remote directory: {current_path}")
                except IOError:
                    pass  # Directory might already exist

        except Exception as e:
            logger.warning(f"Error creating remote directories: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
