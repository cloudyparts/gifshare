GifShare
========

A command-line tool to upload images to S3, for sharing over IRC or whatever.
Supports copying the image from the Web to your S3 bucket, and file renaming.

![Don't try this at home, kids](http://gifs.ninjarockstar.guru/kitty-throw.gif)


Requirements
------------

* Python 2.7 (it might run on earlier versions)
* libmagic (install on OSX with `brew install libmagic`, or on debian/ubuntu
  with `sudo apt-get install file`
* An AWS account


Installation
------------

At the moment

* Run `pip install -r requirements.txt`
* Copy `gifshare` into your path somewhere.
* Create a file at ~/.gifshare - it should be an ini file, and should contain
  the following:

    ```ini
    [default]
    aws_access_id=<your-aws-access-id>
    aws_secret_access_key=<your-aws-secret-access-key>
    web_root=<http://your.s3.bucket.domain.name/>
    region=<aws-region-code>
    bucket=<your-bucket-name>
    ```


Usage
-----

The most common usages are probably the following:

    gifshare /path/to/my.gif

... will upload my.gif to your S3 bucket, and print out the URL of the
uploaded gif.

    gifshare http://funnygifz.guru/a/funny.gif

... will upload funny.gif to your S3 bucket and print out the URL of the
uploaded gif.

You can rename a file with a second argument - do not add the filetype suffix!

    gifshare /path/to/my.gif kitty-hates-whales

... will upload my.gif to your S3 bucket with the new name
'kitty-hates-whales.gif'.  If the file *isn't* a gif, it will rename it with
the correct suffix - one of .gif, .jpeg, or .png. If your file isn't one of
these types, gifshare will exit with an error.

### Advanced Usage

You'll usually want the new URL on your clipboard so you can paste it into your
IRC channel or wherever. Because gifshare prints out the new URL, you can pipe
it to your operating system's clipboard utility! On OSX, this is:

    gifshare /path/to/my.gif funniest-gif-evarr | pbcopy

When gifshare has completed the upload, you can then switch to your chat app
and hit paste. Funny pic goodness, guaranteed.
