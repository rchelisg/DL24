import traceback

if __name__ == "__main__":
    try:
        import main
        app = main.QApplication([])
        window = main.DL24App()
        window.show()
        app.exec()
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())
        input("Press Enter to exit...")