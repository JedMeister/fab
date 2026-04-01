import shutil
import subprocess
import sys
import tempfile
from argparse import ArgumentParser
from os.path import exists, join

from fablib.utils import packages_installed


def gen_iso_parser() -> ArgumentParser:
    parser = ArgumentParser()

    parser.add_argument("build")

    return parser


class ISOBuilder:
    """Build hybrid BIOS/UEFI bootable ISO with GRUB."""

    def __init__(
        self,
        iso_dir: str,
        output_iso: str,
        volume_id: str = "TurnKey Linux",
        uefi: bool = True,
    ) -> None:
        self.iso_dir = iso_dir
        self.output_iso = output_iso
        self.volume_id = volume_id
        self.grub_dir = join(iso_dir, "boot", "grub")
        self.uefi = uefi

        # Validate paths
        if not exists(iso_dir):
            raise FileNotFoundError(f"ISO directory not found: {self.iso_dir}")


    def check_dependencies(self) -> None:
        """Check if required tools are installed.

        grub-common     - grub-mkimage & grub-mkstandalone
        xorriso         - xorriso
        dosfstools      - mkfs.vfat (optional - required for UEFI support)

        dd also required, but not checked as it is part of coreutils (essential
        package).
        """
        dependencies = ["grub-common", "xorriso"]
        if self.uefi:
            dependencies.append("dosfstools")

        not_installed = []

        for package, status in packages_installed(dependencies):
            if status is True:
                continue
            if 
        missing = []
        for pkg, cmds in required_tools.items():
            for cmd in cmds:
                if not shutil.which(cmd):
                    missing.append(pkg)

        if missing:
            print(
                "Error: Missing required tools:",
                ", ".join(missing),
                file=sys.stderr,
            )
            print("\nInstall with:", file=sys.stderr)
            print(
                "  apt-get install grub-pc-bin grub-efi-amd64-bin grub-efi-ia32-bin \\",
                file=sys.stderr,
            )
            print(
                "                  xorriso mtools dosfstools", file=sys.stderr
            )
            sys.exit(1)

    def create_directories(self) -> None:
        """Create necessary directory structure."""
        print("Creating directory structure...")
        self.grub_dir.mkdir(parents=True, exist_ok=True)
        (self.iso_dir / "EFI" / "boot").mkdir(parents=True, exist_ok=True)

    def copy_background_image(self) -> bool:
        """Copy background image from isolinux directory."""
        background_source = self.iso_dir / "isolinux" / "splash.png"
        background_dest = self.grub_dir / "background.png"

        if background_source.exists():
            print(f"Copying background image from {background_source}...")
            shutil.copy2(background_source, background_dest)
            return True
        else:
            print(f"Warning: Background image not found at {background_source}")
            return False

    def create_grub_config(self) -> None:
        """Create GRUB configuration file with background support."""
        print("Creating GRUB configuration...")

        grub_cfg = self.grub_dir / "grub.cfg"

        config_content = """\
set timeout=5
set default=0

# Load graphics modules
if [ "${grub_platform}" == "efi" ]; then
    insmod efi_gop
    insmod efi_uga
else
    insmod vbe
    insmod vga
fi

# Enable graphical terminal and load PNG support
insmod gfxterm
insmod png
set gfxmode=auto
terminal_output gfxterm

# Set background image
if background_image /boot/grub/background.png; then
    set color_normal=light-gray/black
    set color_highlight=white/blue
    set menu_color_normal=light-gray/black
    set menu_color_highlight=white/blue
else
    set color_normal=white/black
    set color_highlight=black/light-gray
fi

menuentry "Live System" {
    linux /live/vmlinuz boot=live quiet splash
    initrd /live/initrd.img
}

menuentry "Install System" {
    linux /live/vmlinuz boot=live quiet splash auto-installer
    initrd /live/initrd.img
}

menuentry "Live System (Safe Mode)" {
    linux /live/vmlinuz boot=live quiet splash nomodeset
    initrd /live/initrd.img
}
"""

        grub_cfg.write_text(config_content)

    def create_bios_boot_image(self) -> None:
        """Create GRUB BIOS boot image."""
        print("Creating GRUB BIOS boot image...")

        bios_img = self.grub_dir / "bios.img"
        core_img = self.grub_dir / "core.img"

        # List of modules for BIOS boot
        modules = [
            "biosdisk",
            "iso9660",
            "part_gpt",
            "part_msdos",
            "normal",
            "boot",
            "linux",
            "configfile",
            "search",
            "search_fs_uuid",
            "search_fs_file",
            "loadenv",
            "ls",
            "cat",
            "echo",
            "test",
            "true",
            "help",
            "gzio",
            "png",
            "vbe",
            "vga",
            "gfxterm",
            "gfxterm_background",
        ]

        # Create core image
        cmd = [
            "grub-mkimage",
            "--format=i386-pc",
            f"--output={core_img}",
            "--prefix=/boot/grub",
            "--compression=auto",
        ] + modules

        subprocess.run(cmd, check=True)

        # Combine boot.img and core.img
        boot_img_source = Path("/usr/lib/grub/i386-pc/boot.img")

        with open(bios_img, "wb") as out_file:
            with open(boot_img_source, "rb") as boot_file:
                out_file.write(boot_file.read())
            with open(core_img, "rb") as core_file:
                out_file.write(core_file.read())

        # Clean up temporary core image
        core_img.unlink()

        # Copy GRUB modules
        grub_modules_dir = self.grub_dir / "i386-pc"
        grub_modules_dir.mkdir(exist_ok=True)

        source_modules = Path("/usr/lib/grub/i386-pc")
        if source_modules.exists():
            for pattern in ["*.mod", "*.lst"]:
                for src_file in source_modules.glob(pattern):
                    try:
                        shutil.copy2(src_file, grub_modules_dir)
                    except Exception:
                        pass  # Ignore copy errors for individual modules

    def create_efi_boot_image(self) -> None:
        """Create GRUB EFI boot image."""
        print("Creating GRUB EFI boot image...")

        efi_img = self.grub_dir / "efi.img"

        # Create FAT filesystem image
        subprocess.run(
            ["dd", "if=/dev/zero", f"of={efi_img}", "bs=1M", "count=10"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        subprocess.run(
            ["mkfs.vfat", str(efi_img)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Mount EFI image
        with tempfile.TemporaryDirectory() as efi_mount:
            efi_mount_path = Path(efi_mount)

            subprocess.run(
                ["mount", "-o", "loop", str(efi_img), str(efi_mount_path)],
                check=True,
            )

            try:
                # Create directory structure
                efi_boot_dir = efi_mount_path / "EFI" / "boot"
                efi_boot_dir.mkdir(parents=True, exist_ok=True)

                # Copy background image into EFI image
                grub_dir_in_efi = efi_mount_path / "boot" / "grub"
                grub_dir_in_efi.mkdir(parents=True, exist_ok=True)

                background_src = self.grub_dir / "background.png"
                if background_src.exists():
                    shutil.copy2(
                        background_src, grub_dir_in_efi / "background.png"
                    )

                # Create standalone GRUB EFI bootloader (64-bit)
                subprocess.run(
                    [
                        "grub-mkstandalone",
                        "--format=x86_64-efi",
                        f"--output={efi_boot_dir / 'bootx64.efi'}",
                        "--locales=",
                        "--fonts=",
                        f"boot/grub/grub.cfg={self.grub_dir / 'grub.cfg'}",
                    ],
                    check=True,
                )

                # Create standalone GRUB EFI bootloader (32-bit)
                subprocess.run(
                    [
                        "grub-mkstandalone",
                        "--format=i386-efi",
                        f"--output={efi_boot_dir / 'bootia32.efi'}",
                        "--locales=",
                        "--fonts=",
                        f"boot/grub/grub.cfg={self.grub_dir / 'grub.cfg'}",
                    ],
                    check=True,
                )

            finally:
                # Unmount EFI image
                subprocess.run(["umount", str(efi_mount_path)], check=True)

    def create_iso(self) -> None:
        """Create the hybrid ISO using xorriso."""
        print("Creating hybrid ISO with xorriso...")

        cmd = [
            "xorriso",
            "-as",
            "mkisofs",
            "-iso-level",
            "3",
            "-full-iso9660-filenames",
            "-volid",
            self.volume_id,
            "-appid",
            "Custom Debian Installer",
            "-publisher",
            "Your Organization",
            "-preparer",
            "GRUB Hybrid Build Script",
            # BIOS boot
            "-eltorito-boot",
            "boot/grub/bios.img",
            "-no-emul-boot",
            "-boot-load-size",
            "4",
            "-boot-info-table",
            "--grub2-boot-info",
            "--grub2-mbr",
            "/usr/lib/grub/i386-pc/boot_hybrid.img",
            # UEFI boot
            "-eltorito-alt-boot",
            "-e",
            "boot/grub/efi.img",
            "-no-emul-boot",
            "-isohybrid-gpt-basdat",
            # Output
            "-output",
            str(self.output_iso),
            str(self.iso_dir),
        ]

        subprocess.run(cmd, check=True)

    def build(self) -> None:
        """Execute the complete build process."""
        print("=" * 70)
        print("Creating hybrid BIOS/UEFI bootable ISO with GRUB and background")
        print("=" * 70)

        self.check_dependencies()
        self.create_directories()
        self.copy_background_image()
        self.create_grub_config()
        self.create_bios_boot_image()
        self.create_efi_boot_image()
        self.create_iso()

        print()
        print("=" * 70)
        print("✓ Hybrid BIOS/UEFI ISO created successfully!")
        print(f"  Output: {self.output_iso}")
        print("=" * 70)
        print()
        print("You can now:")
        print(f"  1. Burn to CD/DVD: wodim -v {self.output_iso}")
        print(
            f"  2. Write to USB:   dd if={self.output_iso} of=/dev/sdX bs=4M status=progress"
        )
        print("  3. Test with QEMU:")
        print(f"     BIOS: qemu-system-x86_64 -cdrom {self.output_iso} -m 2048")
        print(
            f"     UEFI: qemu-system-x86_64 -bios /usr/share/ovmf/OVMF.fd -cdrom {self.output_iso} -m 2048"
        )
        print()


def main():
    """Main entry point."""
    # Configuration
    ISO_DIR = "iso_root"
    OUTPUT_ISO = "custom-debian.iso"
    VOLUME_ID = "CUSTOM_DEBIAN"

    # Parse command line arguments (basic implementation)
    if len(sys.argv) > 1:
        ISO_DIR = sys.argv[1]
    if len(sys.argv) > 2:
        OUTPUT_ISO = sys.argv[2]
    if len(sys.argv) > 3:
        VOLUME_ID = sys.argv[3]

    try:
        builder = ISOBuilder(ISO_DIR, OUTPUT_ISO, VOLUME_ID)
        builder.build()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed: {e.cmd}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBuild cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
