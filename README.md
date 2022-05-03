# Tibis

![image](https://user-images.githubusercontent.com/5250807/166554591-47e85ac2-2f59-4e33-ba95-a76f2ea41818.png)


Tibis (Thot the IBIS) is a tool to help manage encrypted directories (named data container here) 

Name is inspired by the Egyptian god of writers and protector of knowledge 

## TLDR; Setup 

```
pip install tibis
```

## TLDR; Usage 

### Customise the data location path

Default config is set to be at : 
```
~/.config/tibis/config.yml
```
You HAVE TO edit the storage_path to something more secure than /tmp :) 

### Create a new data container
```
tibis create <name>
```
Thot will ask you a passphrase, choose a good one !

### List data containers
```
tibis list 
```

### Mount a data container 
```
tibis unlock <name> <destination path>
```
Thot will ask your passphrase.

### Lock a data container
```
tibis lock <name>
```
Thot will not ask your passphrase.. because it's PGP Public key.

### Remove an entry 
```
tibis delete <name>
```
Thot will ask you a confirmation, take care !
## Why ? 
Because we have to handle with sensitive files, and store them securly can be boring

## How ? 
Tibis is a kind of python wrapper on pgp keys and gzip files. 

Yes, nothing more. 

## Why do we have to set passphrase ? 
Security is a matter of trust, if you don't trust your laptop enough to store sensitive data, why leave the keys in it ?

By using a passphrase, access to the data needs : something you have ( data / key ) and something you know ( passphrase ) 
