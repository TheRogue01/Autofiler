# AutoFiler 🗂️

Ever opened your Downloads folder and been greeted by hundreds of files scattered everywhere?

Screenshots, PDFs, videos, ZIP files, code projects—everything mixed together in one place.

That's why I built AutoFiler.

## What is AutoFiler?

AutoFiler is a desktop application that helps organize cluttered folders quickly and efficiently. Instead of sorting files manually, AutoFiler categorizes them based on their file types and moves them into dedicated folders with a single click.

It's a simple solution to a problem most of us deal with every day: messy file systems.

## Features

### File Type Organization

Automatically sorts files into categories such as:

* Images
* Documents
* Videos
* Music
* Code
* Archives
* And more

### Duplicate File Detection

Uses MD5 hashing to identify duplicate files and prevent unnecessary copies from taking up storage space.

### Activity Logging

Every operation is recorded with a timestamp, making it easy to review changes and track file movements.

### Undo Functionality

Accidentally organized something you didn't mean to? Easily reverse previous actions with a single click.

### Simple Desktop Interface

Built with Tkinter to provide a lightweight and easy-to-use graphical interface.

## Getting Started

Install the required dependency:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python main.py
```

## Built With

* Python
* Tkinter
* Watchdog

## Why I Built This

AutoFiler started as an Operating Systems course project, but it was inspired by a problem I kept running into myself.

My Downloads folder would gradually turn into a dumping ground for screenshots, documents, compressed files, and random projects. Finding a specific file became harder as the clutter grew.

I wanted a tool that could organize everything in a single action and save the time spent sorting files manually.

AutoFiler is the result—a straightforward file organizer that makes keeping folders tidy faster and easier.
