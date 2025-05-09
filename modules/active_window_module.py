import sys
import logging

logger = logging.getLogger(__name__)

def get_active_window_title():
    """
    Gets the title or process name of the currently active window.
    Returns the name as a string, or None if it cannot be determined or an error occurs.
    """
    try:
        if sys.platform == "win32":
            try:
                import win32gui
                import win32process
                import psutil
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    # Get the process ID
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid:
                        process = psutil.Process(pid)
                        # Using process name is often more reliable than window title
                        # You could also use win32gui.GetWindowText(hwnd) for the title
                        title = process.name()
                        logger.debug(f"Active window (Windows): {title}") # Changed to debug
                        return title
                return None
            except ImportError:
                logger.error("Windows: pywin32 or psutil not installed. Active window tracking disabled.")
                return None
            except Exception as e:
                logger.error(f"Windows: Error getting active window: {e}")
                return None
        elif sys.platform.startswith("linux"):
            try:
                from Xlib import display, X
                d = display.Display()
                root = d.screen().root
                active_window_id_prop = d.intern_atom('_NET_ACTIVE_WINDOW')
                active_window_id = root.get_full_property(active_window_id_prop, X.AnyPropertyType)

                if active_window_id and active_window_id.value:
                    window_id = active_window_id.value[0]
                    active_window = d.create_resource_object('window', window_id)
                    
                    # Try _NET_WM_NAME first (UTF-8)
                    net_wm_name_atom = d.intern_atom('_NET_WM_NAME')
                    net_wm_name_prop = active_window.get_full_property(net_wm_name_atom, d.intern_atom('UTF8_STRING'))
                    if net_wm_name_prop and net_wm_name_prop.value:
                        title = net_wm_name_prop.value.decode('utf-8', 'ignore').strip()
                        logger.debug(f"Active window (Linux Xlib _NET_WM_NAME): {title}") # Changed to debug
                        return title

                    # Fallback to WM_NAME (legacy)
                    wm_name = active_window.get_wm_name()
                    if wm_name: # wm_name can be bytes or str depending on Xlib version/setup
                        if isinstance(wm_name, bytes):
                            try:
                                title = wm_name.decode('utf-8', 'ignore').strip()
                                logger.debug(f"Active window (Linux Xlib WM_NAME bytes): {title}") # Changed to debug
                                return title
                            except UnicodeDecodeError:
                                try:
                                    title = wm_name.decode('latin-1', 'ignore').strip() # Common fallback encoding
                                    logger.debug(f"Active window (Linux Xlib WM_NAME latin-1): {title}") # Changed to debug
                                    return title
                                except:
                                    pass # give up on wm_name
                        elif isinstance(wm_name, str):
                            title = wm_name.strip()
                            logger.debug(f"Active window (Linux Xlib WM_NAME str): {title}") # Changed to debug
                            return title
                    
                    # Fallback to WM_CLASS
                    wm_class_atom = d.intern_atom('WM_CLASS')
                    wm_class_prop = active_window.get_full_property(wm_class_atom, X.AnyPropertyType)
                    if wm_class_prop and wm_class_prop.value:
                        # WM_CLASS is a list of null-terminated strings.
                        # Typically [instance_name, class_name]
                        class_strings = wm_class_prop.value.split(b'\\x00')
                        title_to_return = None
                        if len(class_strings) > 1 and class_strings[1]: # Use class_name
                             title_to_return = class_strings[1].decode('utf-8', 'ignore').strip()
                        elif class_strings[0]: # Or instance_name
                             title_to_return = class_strings[0].decode('utf-8', 'ignore').strip()
                        
                        if title_to_return:
                            logger.debug(f"Active window (Linux Xlib WM_CLASS): {title_to_return}") # Changed to debug
                            return title_to_return

                # If Xlib fails, try xdotool as a fallback
                raise ImportError("Falling back to xdotool")

            except ImportError: # Catches Xlib import error or the explicit raise for fallback
                logger.info("Linux: python-xlib not available or failed, trying xdotool.")
                import subprocess
                try:
                    result = subprocess.run(
                        ['xdotool', 'getactivewindow', 'getwindowname'],
                        capture_output=True, text=True, check=True, encoding='utf-8'
                    )
                    title = result.stdout.strip()
                    logger.debug(f"Active window (Linux xdotool): {title}") # Changed to debug
                    return title
                except (subprocess.CalledProcessError, FileNotFoundError):
                    logger.error("Linux: xdotool not installed or failed to get active window.")
                    return None
                except Exception as e:
                    logger.error(f"Linux: xdotool error: {e}")
                    return None
            except Exception as e:
                logger.error(f"Linux: Error getting active window with Xlib: {e}")
                return None
        # macOS (Example, not implemented as per request)
        # elif sys.platform == "darwin":
        #     try:
        #         from AppKit import NSWorkspace
        #         active_app_name = NSWorkspace.sharedWorkspace().frontmostApplication().localizedName()
        #         return active_app_name
        #     except ImportError:
        #         logger.error("macOS: PyObjC (AppKit) not installed.")
        #         return None
        #     except Exception as e:
        #         logger.error(f"macOS: Error getting active window: {e}")
        #         return None
        else:
            logger.warning(f"Unsupported platform for active window tracking: {sys.platform}")
            return None
    except Exception as e:
        logger.error(f"General error in get_active_window_title: {e}")
        return None

if __name__ == '__main__':
    # Test the function
    # Setup basic logging for testing
    logging.basicConfig(level=logging.WARNING) # Changed to WARNING for less verbose test output
    logger.info("Attempting to get active window title...")
    title = get_active_window_title()
    if title:
        logger.info(f"Currently active window/app: {title}")
    else:
        logger.warning("Could not determine active window/app.")
